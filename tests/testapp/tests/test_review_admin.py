from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.test.utils import override_settings


from reviews.admin import ReviewAdmin
from reviews.models import Review
from reviews.widgets import ObjectPkWidget

from . import ReviewTestCase


class MockSuperUser:
    def has_perm(self, perm):
        return True


@override_settings(ROOT_URLCONF='testapp.urls_admin')
class ReviewAdminTests(ReviewTestCase):

    def setUp(self):
        super().setUp()
        site = AdminSite()
        self.admin = ReviewAdmin(Review, site)
        request_factory = RequestFactory()
        self.request = request_factory.get('/admin')
        self.request.user = MockSuperUser()

    def testDeleteReview(self):
        self.createSomeReviews()
        review = Review.objects.get(pk=1)
        self.admin.delete_model(self.request, review)
        deleted = Review.objects.filter(pk=1).first()
        self.assertEqual(deleted, None)

    def testObjectPkWidget(self):
        self.createSomeReviews()
        widget = ObjectPkWidget(Review.objects.get(pk=1))
        html = widget.render('object_pk', 1, attrs={})
        self.assertHTMLEqual(html, '<input type="text" name="object_pk" value="1">&nbsp;&nbsp;<strong><a href="/admin/testapp/article/1/change/">Man Bites Dog</a></strong>')
