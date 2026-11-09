from importlib import import_module
from importlib.util import find_spec
from io import StringIO
from unittest import skipIf, skipUnless

from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.test.utils import modify_settings, override_settings

import reviews
from reviews.models import Review
from reviews.forms import ReviewForm

from . import ReviewTestCase


HAS_DRF = find_spec('rest_framework') is not None


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

    def testGetSiteId(self):
        self.assertEqual(reviews.get_review_site_id(None), 1)
        self.assertEqual(reviews.get_review_site_id(RequestFactory().get('/')), 1)

    @override_settings(SITE_ID=None)
    def testGetSiteIdFromRequest(self):
        self.addCleanup(Site.objects.clear_cache)
        site = Site.objects.create(domain='testserver', name='testserver')
        self.assertEqual(reviews.get_review_site_id(RequestFactory().get('/')), site.pk)
        self.assertIsNone(reviews.get_review_site_id(None))

    def testGetRatingText(self):
        self.assertEqual(reviews.get_review_rating_text(4), 'Very Good')
        self.assertEqual(reviews.get_review_rating_text('4'), 'Very Good')
        self.assertEqual(reviews.get_review_rating_text(1), 'Terrible')
        self.assertEqual(reviews.get_review_rating_text(5), 'Excellent')

    def testGetRatingTextRounding(self):
        self.assertEqual(reviews.get_review_rating_text(3.6), 'Very Good')
        self.assertEqual(reviews.get_review_rating_text(3.4), 'Average')
        self.assertEqual(reviews.get_review_rating_text(1.2), 'Terrible')

    def testGetRatingTextOutOfRange(self):
        self.assertEqual(reviews.get_review_rating_text(0), 'Terrible')
        self.assertEqual(reviews.get_review_rating_text(0.2), 'Terrible')
        self.assertEqual(reviews.get_review_rating_text(-1), 'Terrible')
        self.assertEqual(reviews.get_review_rating_text(5.4), 'Excellent')
        self.assertEqual(reviews.get_review_rating_text(10), 'Excellent')

    @override_settings(REVIEW_RATING_CHOICES=(('1', 'Bad'), ('2', 'Good')))
    def testGetRatingTextCustomChoices(self):
        self.assertEqual(reviews.get_review_rating_text(1), 'Bad')
        self.assertEqual(reviews.get_review_rating_text(2), 'Good')
        self.assertEqual(reviews.get_review_rating_text(5), 'Good')

    @skipUnless(HAS_DRF, "Django REST framework is not installed")
    def testGetApiUserSerializer(self):
        from reviews.api import UserSerializer
        self.assertEqual(reviews.get_review_api_user_serializer(), UserSerializer)

    @skipUnless(HAS_DRF, "Django REST framework is not installed")
    def testGetApiPaginationClass(self):
        from reviews.api import ReviewPagination
        self.assertEqual(reviews.get_review_api_pagination_class(), ReviewPagination)


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

    def testGetSiteId(self):
        self.assertEqual(reviews.get_review_site_id(None), 42)
        self.assertEqual(reviews.get_review_site_id(RequestFactory().get('/')), 42)

    def testGetRatingText(self):
        self.assertEqual(reviews.get_review_rating_text(4), 'custom 4')

    @skipUnless(HAS_DRF, "Django REST framework is not installed")
    def testGetApiDefaults(self):
        # Custom app does not define API hooks, defaults are used
        from reviews.api import ReviewPagination, UserSerializer
        self.assertEqual(reviews.get_review_api_user_serializer(), UserSerializer)
        self.assertEqual(reviews.get_review_api_pagination_class(), ReviewPagination)


class MigrationTests(TestCase):

    def testNoMissingMigrations(self):
        """
        Migrations should match models regardless of project settings, e.g.
        DEFAULT_AUTO_FIELD (test settings intentionally use AutoField).
        """
        out = StringIO()
        try:
            call_command('makemigrations', 'reviews', check=True, dry_run=True, stdout=out, stderr=StringIO())
        except SystemExit:
            self.fail("Reviews models have changes that are not reflected in migrations:\n" + out.getvalue())


@skipIf(HAS_DRF, "Django REST framework is installed")
class NoRestFrameworkTests(SimpleTestCase):

    def testApiRequiresRestFramework(self):
        with self.assertRaisesMessage(ImportError, "pip install django-rated-reviews[api]"):
            import_module('reviews.api')

    def testAppWorksWithoutRestFramework(self):
        # Everything except API should be importable
        for module in ('reviews.admin', 'reviews.forms', 'reviews.models', 'reviews.templatetags.reviews',
                       'reviews.urls', 'reviews.views'):
            import_module(module)
