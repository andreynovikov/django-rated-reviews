from django.urls import reverse

from . import views
from .forms import CustomReviewForm


def get_review_model():
    from .models import CustomReview
    return CustomReview


def get_review_form():
    return CustomReviewForm


def get_review_form_target():
    return reverse(views.custom_submit_review)


def get_review_user_weight(user, target):
    return 2
