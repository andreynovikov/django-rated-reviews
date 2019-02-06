from django import template
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Sum, F, FloatField
from django.db.models.functions import Cast
from django.forms.models import model_to_dict
from django.utils.encoding import smart_text
from django.urls import reverse

from .. import get_model, get_form, get_form_target, DEFAULT_REVIEW_RATING_CHOICES


SHOW_RATING_TEXT = getattr(settings, 'REVIEW_SHOW_RATING_TEXT', True)
REVIEW_RATING_CHOICES = getattr(settings, 'REVIEW_RATING_CHOICES', DEFAULT_REVIEW_RATING_CHOICES)


register = template.Library()


class BaseReviewNode(template.Node):
    """
    Base helper class (abstract) for handling the get_review_* template tags.
    Looks a bit strange, but the subclasses below should make this a bit more
    obvious.
    """

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse get_review_list/count/form and return a Node."""
        tokens = token.split_contents()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% get_whatever for obj as varname %}
        if len(tokens) == 5:
            if tokens[3] != 'as':
                raise template.TemplateSyntaxError("Third argument in %r must be 'as'" % tokens[0])
            return cls(
                object_expr=parser.compile_filter(tokens[2]),
                as_varname=tokens[4],
            )

        # {% get_whatever for app.model pk as varname %}
        elif len(tokens) == 6:
            if tokens[4] != 'as':
                raise template.TemplateSyntaxError("Fourth argument in %r must be 'as'" % tokens[0])
            return cls(
                ctype=BaseReviewNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3]),
                as_varname=tokens[5]
            )

        else:
            raise template.TemplateSyntaxError("%r tag requires 4 or 5 arguments" % tokens[0])

    @staticmethod
    def lookup_content_type(token, tagname):
        try:
            app, model = token.split('.')
            return ContentType.objects.get_by_natural_key(app, model)
        except ValueError:
            raise template.TemplateSyntaxError("Third argument in %r must be in the format 'app.model'" % tagname)
        except ContentType.DoesNotExist:
            raise template.TemplateSyntaxError("%r tag has non-existant content-type: '%s.%s'" % (tagname, app, model))

    def __init__(self, ctype=None, object_pk_expr=None, object_expr=None, as_varname=None, review=None):
        if ctype is None and object_expr is None:
            raise template.TemplateSyntaxError(
                "Review nodes must be given either a literal object or a ctype and object pk.")
        self.review_model = get_model()
        self.as_varname = as_varname
        self.ctype = ctype
        self.object_pk_expr = object_pk_expr
        self.object_expr = object_expr
        self.review = review
        self.filter_public = True

    def render(self, context):
        qs = self.get_queryset(context)
        context[self.as_varname] = self.get_context_value_from_queryset(context, qs)
        return ''

    def get_queryset(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if not object_pk:
            return self.review_model.objects.none()

        # Explicit SITE_ID takes precedence over request. This is also how
        # get_current_site operates.
        site_id = getattr(settings, "SITE_ID", None)
        if not site_id and ('request' in context):
            site_id = get_current_site(context['request']).pk

        qs = self.review_model.objects.filter(
            content_type=ctype,
            object_pk=smart_text(object_pk),
            site__pk=site_id,
        )

        # The is_public field is implementation details of the
        # built-in review model's spam filtering system, so it might not
        # be present on a custom review model subclass. If it exists, we
        # should filter on it.
        field_names = [f.name for f in self.review_model._meta.fields]
        if self.filter_public and 'is_public' in field_names:
            qs = qs.filter(is_public=True)
        if 'user' in field_names:
            qs = qs.select_related('user')
        return qs

    def get_target_ctype_pk(self, context):
        if self.object_expr:
            try:
                obj = self.object_expr.resolve(context)
            except template.VariableDoesNotExist:
                return None, None
            return ContentType.objects.get_for_model(obj), obj.pk
        else:
            return self.ctype, self.object_pk_expr.resolve(context, ignore_failures=True)

    def get_context_value_from_queryset(self, context, qs):
        """Subclasses should override this."""
        raise NotImplementedError


class ReviewListNode(BaseReviewNode):
    """Insert a list of reviews into the context."""

    def get_context_value_from_queryset(self, context, qs):
        return qs


class ReviewCountNode(BaseReviewNode):
    """Insert a count of reviews into the context."""

    def get_context_value_from_queryset(self, context, qs):
        return qs.count()


class ReviewByUserNode(BaseReviewNode):
    """Insert a user review into the context."""
    def __init__(self, *args, **kwargs):
        super(ReviewByUserNode, self).__init__(*args, **kwargs)
        self.filter_public = False

    def get_context_value_from_queryset(self, context, qs):
        field_names = [f.name for f in self.review_model._meta.fields]
        if 'user' in field_names and ('request' in context) and context['request'].user:
            return qs.filter(user=context['request'].user).first()
        else:
            return self.review_model.objects.none()


class ReviewFormNode(BaseReviewNode):
    """Insert a form for the review model into the context."""

    def get_form(self, context):
        obj = self.get_object(context)
        if obj:
            field_names = [f.name for f in self.review_model._meta.fields]
            if 'user' in field_names and ('request' in context) and context['request'].user:
                site_id = getattr(settings, "SITE_ID", None)
                if not site_id and ('request' in context):
                    site_id = get_current_site(context['request']).pk
                try:
                    content_type = ContentType.objects.get_for_model(obj)
                    review = self.review_model.objects.get(
                        content_type=content_type,
                        object_pk=smart_text(obj.pk),
                        site__pk=site_id,
                        user=context['request'].user
                    )
                    return get_form()(obj, initial=model_to_dict(review))
                except self.review_model.DoesNotExist:
                    pass
            return get_form()(obj)
        else:
            return None

    def get_object(self, context):
        if self.object_expr:
            try:
                return self.object_expr.resolve(context)
            except template.VariableDoesNotExist:
                return None
        else:
            object_pk = self.object_pk_expr.resolve(context, ignore_failures=True)
            return self.ctype.get_object_for_this_type(pk=object_pk)

    def render(self, context):
        context[self.as_varname] = self.get_form(context)
        return ''


class RenderReviewFormNode(ReviewFormNode):
    """Render the review form directly"""

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse render_review_form and return a Node."""
        tokens = token.split_contents()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% render_review_form for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))

        # {% render_review_form for app.models pk %}
        elif len(tokens) == 4:
            return cls(
                ctype=BaseReviewNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3])
            )

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "reviews/%s/%s/form.html" % (ctype.app_label, ctype.model),
                "reviews/%s/form.html" % ctype.app_label,
                "reviews/form.html"
            ]
            context_dict = context.flatten()
            context_dict['form'] = self.get_form(context)
            context_dict['show_rating_text'] = SHOW_RATING_TEXT
            formstr = render_to_string(template_search_list, context_dict)
            return formstr
        else:
            return ''


class RenderReviewListNode(ReviewListNode):
    """Render the review list directly"""

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse render_review_list and return a Node."""
        tokens = token.split_contents()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% render_review_list for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))

        # {% render_review_list for app.models pk %}
        elif len(tokens) == 4:
            return cls(
                ctype=BaseReviewNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3])
            )

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "reviews/%s/%s/list.html" % (ctype.app_label, ctype.model),
                "reviews/%s/list.html" % ctype.app_label,
                "reviews/list.html"
            ]
            qs = self.get_queryset(context)
            context_dict = context.flatten()
            context_dict['review_list'] = self.get_context_value_from_queryset(context, qs)
            context_dict['rating_choices'] = REVIEW_RATING_CHOICES
            liststr = render_to_string(template_search_list, context_dict)
            return liststr
        else:
            return ''


class RatingAverageNode(BaseReviewNode):
    """Insert a rating weighted average into the context."""

    def get_context_value_from_queryset(self, context, qs):
        # select sum(rating * weight) / sum(weight) as average_rating
        return qs.aggregate(average_rating=Cast(Sum(F('rating') * F('weight')), FloatField()) /
                            Cast(Sum(F('weight')), FloatField()))['average_rating']


class RenderRatingAverageNode(RatingAverageNode):
    """Render the rating weighted average directly"""

    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse render_rating and return a Node."""
        tokens = token.split_contents()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% render_rating for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))

        # {% render_rating for app.models pk %}
        elif len(tokens) == 4:
            return cls(
                ctype=BaseReviewNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3])
            )

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "reviews/%s/%s/rating_average.html" % (ctype.app_label, ctype.model),
                "reviews/%s/rating_average.html" % ctype.app_label,
                "reviews/rating_average.html"
            ]
            qs = self.get_queryset(context)
            count = qs.count()
            context_dict = context.flatten()
            context_dict['rating_choices'] = REVIEW_RATING_CHOICES
            context_dict['show_rating_text'] = SHOW_RATING_TEXT
            context_dict['review_count'] = count
            if count > 0:
                average = self.get_context_value_from_queryset(context, qs)
                context_dict['average_rating'] = '{0:.1f}'.format(average)
                if average < 1:
                    # This can not happen but we should correctly process it
                    context_dict['average_rating_text'] = REVIEW_RATING_CHOICES[0][1]
                else:
                    context_dict['average_rating_text'] = REVIEW_RATING_CHOICES[round(average)-1][1]
                if average < 0.3:
                    # Distinguish reviewed and unreviewed items
                    context_dict['average_rating_star'] = 's05'
                else:
                    context_dict['average_rating_star'] = 's{0:02.0f}'.format(round(average * 2.0) * 5.0)
            ratingstr = render_to_string(template_search_list, context_dict)
            return ratingstr
        else:
            return ''


# We could just register each classmethod directly, but then we'd lose out on
# the automagic docstrings-into-admin-docs tricks. So each node gets a cute
# wrapper function that just exists to hold the docstring.

@register.tag
def get_review_count(parser, token):
    """
    Gets the review count for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_review_count for [object] as [varname]  %}
        {% get_review_count for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_review_count for product as review_count %}
        {% get_review_count for shop.product product.id as review_count %}
        {% get_review_count for shop.product 17 as review_count %}

    """
    return ReviewCountNode.handle_token(parser, token)


@register.tag
def get_review_list(parser, token):
    """
    Gets the list of reviews for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_review_list for [object] as [varname]  %}
        {% get_review_list for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_review_list for product as review_list %}
        {% for review in review_list %}
            ...
        {% endfor %}

    """
    return ReviewListNode.handle_token(parser, token)


@register.tag
def render_review_list(parser, token):
    """
    Render the review list (as returned by ``{% get_review_list %}``)
    through the ``reviews/list.html`` template

    Syntax::

        {% render_review_list for [object] %}
        {% render_review_list for [app].[model] [object_id] %}

    Example usage::

        {% render_review_list for product %}

    """
    return RenderReviewListNode.handle_token(parser, token)


@register.tag
def get_review_by_user(parser, token):
    """
    Gets the current user review for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_review_by_user for [object] as [varname]  %}
        {% get_review_by_user for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_review_by_user for product as user_review %}

    """
    return ReviewByUserNode.handle_token(parser, token)


@register.tag
def get_review_form(parser, token):
    """
    Get a (new) form object to post a new review.

    Syntax::

        {% get_review_form for [object] as [varname] %}
        {% get_review_form for [app].[model] [object_id] as [varname] %}
    """
    return ReviewFormNode.handle_token(parser, token)


@register.tag
def render_review_form(parser, token):
    """
    Render the review form (as returned by ``{% render_review_form %}``) through
    the ``reviews/form.html`` template.

    Syntax::

        {% render_review_form for [object] %}
        {% render_review_form for [app].[model] [object_id] %}
    """
    return RenderReviewFormNode.handle_token(parser, token)


@register.simple_tag
def review_form_target():
    """
    Get the target URL for the review form.

    Example::

        <form action="{% review_form_target %}" method="post">
    """
    return get_form_target()


@register.simple_tag
def get_review_permalink(review, anchor_pattern=None):
    """
    Get the permalink for a review, optionally specifying the format of the
    named anchor to be appended to the end of the URL.

    Example::
        {% get_review_permalink review "#r%(id)s-by-%(user_name)s" %}
    """

    if anchor_pattern:
        return review.get_absolute_url(anchor_pattern)
    return review.get_absolute_url()


@register.tag
def get_rating(parser, token):
    """
    Gets the average rating for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_rating for [object] as [varname]  %}
        {% get_rating for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_rating for product as avg_rating %}
        {% get_rating for shop.product product.id as avg_rating %}
        {% get_rating for shop.product 17 as avg_rating %}

    """
    return RatingAverageNode.handle_token(parser, token)


@register.tag
def render_rating(parser, token):
    """
    Render the rating (as returned by ``{% get_rating %}``)
    through the ``reviews/rating.html`` template

    Syntax::

        {% render_rating for [object] %}
        {% render_rating for [app].[model] [object_id] %}

    Example usage::

        {% render_rating for product %}

    """
    return RenderRatingAverageNode.handle_token(parser, token)


@register.inclusion_tag('reviews/rating_value.html')
def render_rating_value(value):
    """
    Render exact rating through the ``reviews/rating_value.html`` template

    Syntax::

        {% render_rating_value [number] %}

    Example usage::

        {% render_rating_value review.rating %}

    """
    context_dict = {
        'rating_choices': REVIEW_RATING_CHOICES,
        'show_rating_text': SHOW_RATING_TEXT,
        'rating': '{0:.1f}'.format(value)
    }
    if value < 1:
        # This should not happen but we should correctly process it
        context_dict['rating_text'] = REVIEW_RATING_CHOICES[0][1]
    else:
        context_dict['rating_text'] = REVIEW_RATING_CHOICES[int(round(value))-1][1]
    if value < 0.3:
        # Distinguish reviewed and unreviewed items
        context_dict['rating_star'] = 's05'
    else:
        context_dict['rating_star'] = 's{0:02.0f}'.format(round(value * 2.0) * 5.0)
    return context_dict

