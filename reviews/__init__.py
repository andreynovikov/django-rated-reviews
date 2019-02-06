from importlib import import_module

from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _


DEFAULT_REVIEW_APP = 'reviews'
DEFAULT_REVIEW_RATING_CHOICES = (
    ('1', _('Terrible')),
    ('2', _('Poor')),
    ('3', _('Average')),
    ('4', _('Very Good')),
    ('5', _('Excellent')),
)

default_app_config = 'reviews.apps.ReviewsAppConfig'


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


def get_model():
    """
    Returns the review model class.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_model"):
        return get_review_app().get_model()
    else:
        from reviews.models import Review
        return Review


def get_form():
    """
    Returns the review ModelForm class.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_form"):
        return get_review_app().get_form()
    else:
        from reviews.forms import ReviewForm
        return ReviewForm


def get_form_target():
    """
    Returns the target URL for the review form submission view.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_form_target"):
        return get_review_app().get_form_target()
    else:
        return reverse("post-review")


def get_user_weight(user, target):
    """
    Returns the rating weight for specific user.
    """
    if get_review_app_name() != DEFAULT_REVIEW_APP and hasattr(get_review_app(), "get_user_weight"):
        return get_review_app().get_user_weight(user, target)
    else:
        return 1
