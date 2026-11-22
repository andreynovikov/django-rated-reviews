from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_str


def get_user_review(review_model, target, user, site_id=None):
    """
    Return the review that ``user`` has posted about ``target`` on the site,
    the latest one if there are several, or ``None``. Anonymous users have no
    review of their own, nor do review models without ``user`` and ``site``
    fields.
    """
    field_names = {f.name for f in review_model._meta.fields}
    if not {'content_type', 'object_pk', 'site', 'user'} <= field_names:
        return None
    if user is None or not user.is_authenticated:
        return None
    reviews = review_model._default_manager.filter(
        content_type=ContentType.objects.get_for_model(target),
        object_pk=force_str(target._get_pk_val()),
        site__pk=site_id or getattr(settings, 'SITE_ID', None),
        user=user,
    )
    if 'submit_date' in field_names:
        reviews = reviews.order_by('-submit_date', '-pk')
    else:
        reviews = reviews.order_by('-pk')
    return reviews.first()
