"""
Custom reviews app that customizes only REST API related behaviour. Review
model and form are the defaults.
"""

SITE_ID = 2


def get_review_site_id(request):
    return SITE_ID


def get_review_rating_text(rating):
    return "{} of 5".format(round(rating))


def get_review_user_weight(user, target):
    if user.is_staff:
        return 3
    return 1


def get_review_api_user_serializer():
    from .api import CustomUserSerializer
    return CustomUserSerializer


def get_review_api_pagination_class():
    from .api import CustomPagination
    return CustomPagination
