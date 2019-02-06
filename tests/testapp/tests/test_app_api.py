from __future__ import absolute_import

from django.core.exceptions import ImproperlyConfigured
from django.test.utils import modify_settings, override_settings

import reviews
from reviews.models import Review
from reviews.forms import ReviewForm

from . import ReviewTestCase


class ReviewAppAPITests(ReviewTestCase):
    """Tests for the "review app" API"""

    def testGetReviewApp(self):
        self.assertEqual(reviews.get_review_app(), reviews)

    @modify_settings(INSTALLED_APPS={'remove': 'reviews'})
    def testGetMissingReviewApp(self):
        msg = "The REVIEW_APP ('reviews') must be in INSTALLED_APPS"
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            reviews.get_review_app()

    def testGetForm(self):
        self.assertEqual(reviews.get_form(), ReviewForm)

    def testGetFormTarget(self):
        self.assertEqual(reviews.get_form_target(), "/post/")


@override_settings(
    REVIEW_APP='custom_reviews', ROOT_URLCONF='testapp.urls',
)
class CustomReviewTest(ReviewTestCase):

    def testGetReviewApp(self):
        import custom_reviews
        self.assertEqual(reviews.get_review_app(), custom_reviews)

    def testGetModel(self):
        from custom_reviews.models import CustomReview
        self.assertEqual(reviews.get_model(), CustomReview)

    def testGetForm(self):
        from custom_reviews.forms import CustomReviewForm
        self.assertEqual(reviews.get_form(), CustomReviewForm)

    def testGetFormTarget(self):
        self.assertEqual(reviews.get_form_target(), "/post/")
