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

    def testGetModel(self):
        self.assertEqual(reviews.get_review_model(), Review)

    def testGetForm(self):
        self.assertEqual(reviews.get_review_form(), ReviewForm)

    def testGetFormTarget(self):
        self.assertEqual(reviews.get_review_form_target(), "/post/")

    def testGetUserWeight(self):
        r1, _, _, _ = self.createSomeReviews()
        self.assertEqual(reviews.get_review_user_weight(r1.user, r1.content_object), 1)


@override_settings(
    REVIEW_APP='custom_reviews', ROOT_URLCONF='testapp.urls',
)
class CustomReviewTest(ReviewTestCase):

    def testGetReviewApp(self):
        import custom_reviews
        self.assertEqual(reviews.get_review_app(), custom_reviews)

    def testGetModel(self):
        from custom_reviews.models import CustomReview
        self.assertEqual(reviews.get_review_model(), CustomReview)

    def testGetForm(self):
        from custom_reviews.forms import CustomReviewForm
        self.assertEqual(reviews.get_review_form(), CustomReviewForm)

    def testGetFormTarget(self):
        self.assertEqual(reviews.get_review_form_target(), "/post/")

    def testGetUserWeight(self):
        r1, _, _, _ = self.createSomeReviews()
        self.assertEqual(reviews.get_review_user_weight(r1.user, r1.content_object), 2)
