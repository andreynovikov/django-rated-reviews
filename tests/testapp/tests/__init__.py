from __future__ import absolute_import

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.test import TestCase
from django.test.utils import override_settings

from reviews.forms import ReviewForm
from reviews.models import Review

from testapp.models import Article, Product

# Shortcut
CT = ContentType.objects.get_for_model


@override_settings(
    PASSWORD_HASHERS=('django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',),
    ROOT_URLCONF='testapp.urls_default',
)
class ReviewTestCase(TestCase):
    """
    Helper base class for comment tests that need data.
    """
    fixtures = ["review_tests"]

    def createSomeReviews(self):
        u1 = User.objects.create(
            username="frank_nobody",
            first_name="Frank",
            last_name="Nobody",
            email="fnobody@example.com",
            password="",
            is_staff=False,
            is_active=True,
            is_superuser=False,
        )
        u2 = User.objects.create(
            username="joe_uncought",
            first_name="Joe",
            last_name="Uncought",
            email="juncought@example.com",
            password="",
            is_staff=False,
            is_active=True,
            is_superuser=False,
        )
        r1 = Review.objects.create(
            content_type=CT(Article),
            object_pk="1",
            user=u1,
            rating="5",
            comment="Nice article.",
            site=Site.objects.get_current(),
        )
        r2 = Review.objects.create(
            content_type=CT(Product),
            object_pk="1",
            user=u1,
            rating="4",
            comment="It's pretty boxy",
            site=Site.objects.get_current(),
        )
        r3 = Review.objects.create(
            content_type=CT(Product),
            object_pk="2",
            user=u1,
            rating="3",
            comment="It's kinda not foxy",
            site=Site.objects.get_current(),
        )
        r4 = Review.objects.create(
            content_type=CT(Product),
            object_pk="2",
            user=u2,
            rating="4",
            comment="It's not foxy but still suits",
            site=Site.objects.get_current(),
        )

        return r1, r2, r3, r4

    def moderateSomeReviews(self):
        for pk in (1, 4):
            r = Review.objects.get(pk=pk)
            r.is_public = True
            r.save()

    def getData(self):
        return {
            'rating': '4',
            'comment': 'This is my comment',
        }

    def getValidData(self, obj):
        f = ReviewForm(obj)
        d = self.getData()
        d.update(f.initial)
        return d
