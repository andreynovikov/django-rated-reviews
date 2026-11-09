from importlib import import_module

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


DEFAULT_REVIEW_APP = 'reviews'
DEFAULT_REVIEW_RATING_CHOICES = (
    ('1', _('Terrible')),
    ('2', _('Poor')),
    ('3', _('Average')),
    ('4', _('Very Good')),
    ('5', _('Excellent')),
)


def get_review_app():
    """
    Get the review app (i.e. "reviews") as defined in the settings
    """
    # Make sure the app's in INSTALLED_APPS
    review_app = get_review_app_name()
    if not django_apps.is_installed(review_app):
        raise ImproperlyConfigured(
            "The REVIEW_APP (%r) must be in INSTALLED_APPS" % review_app
        )

    # Try to import the package
    try:
        package = import_module(review_app)
    except ImportError as e:
        raise ImproperlyConfigured(
            "The REVIEW_APP setting refers to a non-existing package. (%s)" % e
        )

    return package


def get_review_app_name():
    """
    Returns the name of the reviews app (either the setting value, if it
    exists, or the default).
    """
    return getattr(settings, 'REVIEW_APP', DEFAULT_REVIEW_APP)


def get_review_model():
    """
    Returns the review model class.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_review_model"):
        return get_review_app().get_review_model()
    else:
        from reviews.models import Review
        return Review


def get_review_form():
    """
    Returns the review form class.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_review_form"):
        return get_review_app().get_review_form()
    else:
        from reviews.forms import ReviewForm
        return ReviewForm


def get_review_form_target():
    """
    Returns the target URL for the review form submission view.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_review_form_target"):
        return get_review_app().get_review_form_target()
    else:
        return reverse("post-review")


def get_review_site_id(request):
    """
    Returns the ID of the site that reviews are posted to and listed for.
    ``request`` can be ``None`` (e.g. in templates rendered without request).
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_review_site_id"):
        return get_review_app().get_review_site_id(request)
    else:
        # Explicit SITE_ID takes precedence over request. This is also how
        # get_current_site operates.
        site_id = getattr(settings, "SITE_ID", None)
        if not site_id and request is not None:
            site_id = get_current_site(request).pk
        return site_id


def get_review_rating_text(rating):
    """
    Returns the text describing a rating, e.g. "Very Good" for 4. The value
    can be fractional (an average rating): it is rounded to the nearest grade
    and clamped to the range of REVIEW_RATING_CHOICES.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_review_rating_text"):
        return get_review_app().get_review_rating_text(rating)
    else:
        choices = getattr(settings, 'REVIEW_RATING_CHOICES', DEFAULT_REVIEW_RATING_CHOICES)
        grade = min(max(int(round(float(rating))), 1), len(choices))
        return choices[grade - 1][1]


def get_review_user_weight(user, target):
    """
    Returns the rating weight for specific user.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_review_user_weight"):
        return get_review_app().get_review_user_weight(user, target)
    else:
        return 1


def get_review_api_user_serializer():
    """
    Returns the REST API serializer class for review author.
    Requires Django REST framework.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_review_api_user_serializer"):
        return get_review_app().get_review_api_user_serializer()
    else:
        from reviews.api import UserSerializer
        return UserSerializer


def get_review_api_pagination_class():
    """
    Returns the REST API pagination class for review lists.
    Requires Django REST framework.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_review_api_pagination_class"):
        return get_review_app().get_review_api_pagination_class()
    else:
        from reviews.api import ReviewPagination
        return ReviewPagination
