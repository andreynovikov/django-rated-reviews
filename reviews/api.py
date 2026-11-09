"""
REST API for reviews. Requires Django REST framework:

    pip install django-rated-reviews[api]
"""
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Sum, F, FloatField
from django.db.models.functions import Cast
from django.utils.encoding import smart_str

try:
    from rest_framework import viewsets, serializers
    from rest_framework.decorators import action
    from rest_framework.exceptions import NotFound, ParseError
    from rest_framework.pagination import PageNumberPagination
    from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated, IsAdminUser
    from rest_framework.response import Response
except ImportError as e:
    raise ImportError(
        "reviews.api requires Django REST framework, install it with: "
        "pip install django-rated-reviews[api]"
    ) from e

from . import (
    signals, get_review_model, get_review_form, get_review_site_id, get_review_rating_text,
    get_review_user_weight, get_review_api_user_serializer, get_review_api_pagination_class
)


# Fields that are never exposed and can not be used for filtering
PRIVATE_FIELDS = ('content_type', 'ip_address')


def get_target_object(ctype, object_pk):
    """
    Returns the reviewed object or raises NotFound.
    """
    model = ctype.model_class()
    if model is None:
        raise NotFound("Model does not exist")
    try:
        return model._default_manager.get(pk=object_pk)
    except (model.DoesNotExist, ValueError, DjangoValidationError):
        raise NotFound("Object does not exist")


class IsOwner(BasePermission):
    """
    Allows access only to the author of the review.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return not hasattr(obj, 'user') or obj.user == request.user


class ReviewPagination(PageNumberPagination):
    """
    Default pagination of review lists: 20 reviews per page, page size can be
    changed with ``page_size`` query parameter (up to 1000).
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class UserSerializer(serializers.Serializer):
    """
    Default representation of a review author: its primary key and the same
    text that templates show (``str(user)``). Other user data is deliberately
    not exposed, use REVIEW_APP to provide a custom serializer.
    """
    id = serializers.ReadOnlyField(source='pk')
    name = serializers.CharField(source='__str__', read_only=True)


class ReviewSerializer(serializers.ModelSerializer):
    """
    Read representation of a review.
    """
    class Meta:
        model = get_review_model()
        form = get_review_form()
        model_fields = [f.name for f in model._meta.fields]
        form_fields = [f.name for f in form(model()).visible_fields()]
        read_only_fields = list(set(model_fields).difference(form_fields))
        exclude = PRIVATE_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'user' in self.Meta.model_fields:
            self.fields['user'] = get_review_api_user_serializer()(read_only=True)
        if 'object_pk' in self.context:
            # Object is known from the request, do not repeat it in every review
            self.fields.pop('object_pk', None)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['rating'] = {
            'value': instance.rating,
            'text': get_review_rating_text(instance.rating)
        }
        return representation


class ReviewActionSerializer(serializers.Serializer):
    """
    Creates and updates reviews. Data is validated by the review form, so the
    API applies the same security and content checks as the HTML form.
    """
    target = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'object_pk' in self.context:
            self.target = get_target_object(self.context['ctype'], self.context['object_pk'])
            form = get_review_form()(self.target)
            for field in form:
                if field.name == 'id':
                    continue
                if hasattr(field.field, 'choices'):
                    choices = field.field.choices
                elif hasattr(field.field.widget, 'choices'):
                    choices = field.field.widget.choices
                else:
                    choices = None
                field_args = {
                    'label': field.label,
                    'required': field.field.required
                }
                if field.name == 'honeypot':
                    field_args['allow_blank'] = True
                if choices:
                    self.fields[field.name] = serializers.ChoiceField(choices=choices, **field_args)
                else:
                    self.fields[field.name] = serializers.CharField(**field_args)

    def validate(self, data):
        if self.target is None:
            raise serializers.ValidationError("Reviewed object is not specified")
        form = get_review_form()(self.target, data)
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        self.cleaned_form = form
        return form.cleaned_data

    def save_review(self, review):
        """
        Fill in request dependent fields, save the review and signal that it was saved.
        """
        request = self.context['request']
        review.weight = get_review_user_weight(request.user, self.target)
        review.ip_address = request.META.get("REMOTE_ADDR", None) or None
        review.save()
        signals.review_was_posted.send(sender=review.__class__, review=review, request=request)
        return review

    def create(self, validated_data):
        request = self.context['request']
        review = self.cleaned_form.get_review_object(site_id=get_review_site_id(request))
        if request.user.is_authenticated:
            review.user = request.user
        return self.save_review(review)

    def update(self, instance, validated_data):
        self.cleaned_form.update_review_object(instance)
        return self.save_review(instance)

    def to_representation(self, instance):
        return ReviewSerializer(context=self.context).to_representation(instance)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    Reviews of a particular model or object. The model (``app_label.model``)
    and the object identifier are taken from URL kwargs or query parameters.
    """
    serializer_class = ReviewActionSerializer
    review_model = get_review_model()
    model_fields = [f.name for f in review_model._meta.fields]
    model_url_kwarg = 'model'
    identifier_url_kwarg = 'identifier'
    filter_public = True

    @property
    def pagination_class(self):
        return get_review_api_pagination_class()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        full_model = self.kwargs.get(self.model_url_kwarg, request.query_params.get(self.model_url_kwarg))
        try:
            app_label, model = full_model.split('.')
            self.ctype = ContentType.objects.get_by_natural_key(app_label, model)
        except (AttributeError, ValueError, ContentType.DoesNotExist):
            raise ParseError("Incorrect model: {}".format(full_model))
        self.object_pk = self.kwargs.get(self.identifier_url_kwarg, request.query_params.get(self.identifier_url_kwarg))
        if not self.object_pk and self.action in ('create', 'update', 'partial_update', 'form'):
            raise ParseError("Object identifier is required")

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ('update', 'partial_update'):
            permission_classes = [IsOwner]
        elif self.action == 'destroy':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ctype'] = getattr(self, 'ctype', None)
        if getattr(self, 'object_pk', None):
            context['object_pk'] = self.object_pk
        return context

    def get_queryset(self):
        qs = self.review_model.objects.filter(content_type=self.ctype)
        if self.object_pk:
            qs = qs.filter(object_pk=smart_str(self.object_pk))

        site_id = get_review_site_id(self.request)
        qs = qs.filter(site__pk=site_id)

        # The is_public field is implementation details of the
        # built-in review model's spam filtering system, so it might not
        # be present on a custom review model subclass. If it exists, we
        # should filter on it.
        if self.action in ('list', 'average') and self.filter_public and 'is_public' in self.model_fields:
            qs = qs.filter(is_public=True)

        for field, values in self.request.query_params.lists():
            if field not in self.model_fields or field in PRIVATE_FIELDS:
                continue
            try:
                if len(values) > 1:
                    qs = qs.filter(**{'{}__in'.format(field): values})
                else:
                    qs = qs.filter(**{'{}__exact'.format(field): values[0]})
            except (ValueError, DjangoValidationError):
                raise ParseError("Incorrect value of {}".format(field))

        return qs

    def list(self, request, *args, **kwargs):
        """
        Published reviews. For a particular object the response also contains
        rating ``statistics`` and, for authenticated user, ``user_reviews``.
        """
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200 and self.object_pk and isinstance(response.data, dict):
            qs = self.get_queryset()
            if qs.exists():
                average, text = self.get_average(qs)
                response.data['statistics'] = {
                    'value': average,
                    'text': text,
                    'ratings': list(qs.values('rating').annotate(count=Count('pk')).order_by('rating'))
                }
            if 'user' in self.model_fields and request.user and request.user.is_authenticated:
                qs = self.review_model.objects.filter(
                    content_type=self.ctype,
                    object_pk=smart_str(self.object_pk),
                    site__pk=get_review_site_id(request),
                    user=request.user
                )
                response.data['user_reviews'] = list(qs.values_list('pk', flat=True))
        return response

    @action(detail=False, methods=['get'])
    def average(self, request, *args, **kwargs):
        """
        Weighted average rating of published reviews.
        """
        qs = self.get_queryset()
        count = qs.count()
        if count == 0:
            return Response({'count': count})

        average, text = self.get_average(qs)
        return Response({
            'value': average,
            'text': text,
            'count': count
        })

    @action(detail=False, methods=['get'])
    def form(self, request, *args, **kwargs):
        """
        Description of review form fields, including values of the hidden
        security fields that have to be sent back with a review.
        """
        target = get_target_object(self.ctype, self.object_pk)
        form = get_review_form()(target)
        fields = []
        for field in form:
            if field.name == 'id':
                continue
            meta = {
                'name': field.name,
                'label': field.label,
                'id': field.id_for_label,
                'help': field.help_text,
                'class': field.field.__class__.__name__,
                'widget': field.field.widget.__class__.__name__,
                'required': field.field.required
            }
            if hasattr(field.field, 'choices'):
                meta['choices'] = field.field.choices
            elif hasattr(field.field.widget, 'choices'):
                meta['choices'] = field.field.widget.choices
            if field.field.widget.attrs:
                meta['attrs'] = field.field.widget.attrs
            value = field.value()
            if value is not None:
                meta['value'] = value
            fields.append(meta)
        return Response(fields)

    def get_average(self, queryset):
        # select sum(rating * weight) / sum(weight) as average_rating
        average = queryset.aggregate(
            average_rating=Cast(Sum(F('rating') * F('weight')), FloatField()) / Cast(Sum(F('weight')), FloatField())
        )['average_rating']
        return average, get_review_rating_text(average)
