from django.urls import reverse

from . import views
from .forms import CustomReviewForm


def get_model():
    from .models import CustomReview
    return CustomReview


def get_form():
    return CustomReviewForm


def get_form_target():
    return reverse(views.custom_submit_review)
