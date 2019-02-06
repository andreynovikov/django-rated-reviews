from __future__ import absolute_import

import time

from django.conf import settings
from django.contrib.sites.models import Site

from reviews.forms import ReviewForm
from reviews.models import Review

from . import ReviewTestCase
from testapp.models import Article


class ReviewFormTests(ReviewTestCase):

    def setUp(self):
        super(ReviewFormTests, self).setUp()
        self.site_2 = Site.objects.create(id=settings.SITE_ID + 1,
            domain="testserver", name="testserver")

    def testInit(self):
        f = ReviewForm(Article.objects.get(pk=1))
        self.assertEqual(f.initial['content_type'], str(Article._meta))
        self.assertEqual(f.initial['object_pk'], "1")
        self.assertNotEqual(f.initial['security_hash'], None)
        self.assertNotEqual(f.initial['timestamp'], None)

    def testValidPost(self):
        a = Article.objects.get(pk=1)
        f = ReviewForm(a, data=self.getValidData(a))
        self.assertTrue(f.is_valid(), f.errors)
        return f

    def tamperWithForm(self, **kwargs):
        a = Article.objects.get(pk=1)
        d = self.getValidData(a)
        d.update(kwargs)
        f = ReviewForm(Article.objects.get(pk=1), data=d)
        self.assertFalse(f.is_valid())
        return f

    def testHoneypotTampering(self):
        self.tamperWithForm(honeypot="I am a robot")

    def testTimestampTampering(self):
        self.tamperWithForm(timestamp=str(time.time() - 28800))

    def testSecurityHashTampering(self):
        self.tamperWithForm(security_hash="Nobody expects the Spanish Inquisition!")

    def testContentTypeTampering(self):
        self.tamperWithForm(content_type="auth.user")

    def testObjectPKTampering(self):
        self.tamperWithForm(object_pk="3")

    def testSecurityErrors(self):
        f = self.tamperWithForm(honeypot="I am a robot")
        self.assertTrue("honeypot" in f.security_errors())

    def testGetReviewObject(self):
        f = self.testValidPost()
        r = f.get_review_object()
        self.assertTrue(isinstance(r, Review))
        self.assertEqual(r.content_object, Article.objects.get(pk=1))
        self.assertEqual(r.comment, "This is my comment")
        r.save()
        self.assertEqual(Review.objects.count(), 1)

        # Create a review for the second site. We only test for site_id, not
        # what has already been tested above.
        a = Article.objects.get(pk=1)
        d = self.getValidData(a)
        d["comment"] = "testGetReviewObject with a site"
        f = ReviewForm(Article.objects.get(pk=1), data=d)
        r = f.get_review_object(site_id=self.site_2.id)
        self.assertEqual(r.site_id, self.site_2.id)

    def testProfanities(self):
        """Test REVIEW_ALLOW_PROFANITIES and PROFANITIES_LIST settings"""
        a = Article.objects.get(pk=1)
        d = self.getValidData(a)

        # Save settings in case other tests need 'em
        saved = getattr(settings, 'PROFANITIES_LIST', []), getattr(settings, 'REVIEW_ALLOW_PROFANITIES', False)

        # Don't wanna swear in the unit tests if we don't have to...
        settings.PROFANITIES_LIST = ["rooster"]

        # Try with REVIEW_ALLOW_PROFANITIES off
        settings.REVIEW_ALLOW_PROFANITIES = False
        f = ReviewForm(a, data=dict(d, comment="What a rooster!", rating="4"))
        self.assertFalse(f.is_valid())

        # Now with REVIEW_ALLOW_PROFANITIES on
        settings.REVIEW_ALLOW_PROFANITIES = True
        f = ReviewForm(a, data=dict(d, comment="What a rooster!", rating="4"))
        self.assertTrue(f.is_valid())

        # Restore settings
        settings.PROFANITIES_LIST, settings.REVIEW_ALLOW_PROFANITIES = saved
