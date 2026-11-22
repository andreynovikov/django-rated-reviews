from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test.utils import override_settings
from django.utils import timezone

from reviews import signals
from reviews.models import REVIEW_MAX_LENGTH, Review

from . import CT, ReviewTestCase
from testapp.models import Article, Product


class ReviewViewTests(ReviewTestCase):

    def testPostReviewHTTPMethods(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.get("/post/", data)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "POST")

    def testPostReviewMissingCtype(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        del data["content_type"]
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostReviewBadCtype(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["content_type"] = "Nobody expects the Spanish Inquisition!"
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostReviewMissingObjectPK(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        del data["object_pk"]
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostReviewBadObjectPK(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["object_pk"] = "14"
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostInvalidIntegerPK(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["rating"] = "4"
        data["comment"] = "This is another comment"
        data["object_pk"] = '\ufffd'
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostInvalidDecimalPK(self):
        b = Product.objects.get(pk=1)
        data = self.getValidData(b)
        data["rating"] = "4"
        data["comment"] = "This is another comment"
        data["object_pk"] = 'cookies'
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testPostTooLongComment(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["rating"] = "4"
        data["comment"] = "X" * (REVIEW_MAX_LENGTH + 1)
        response = self.client.post("/post/", data)
        self.assertContains(
            response, "Ensure this value has at most %d characters" % REVIEW_MAX_LENGTH
        )

    def testHashTampering(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["security_hash"] = "Nobody expects the Spanish Inquisition!"
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)

    def testDebugReviewErrors(self):
        """The debug error template should be shown only if DEBUG is True"""
        olddebug = settings.DEBUG

        settings.DEBUG = True
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["security_hash"] = "Nobody expects the Spanish Inquisition!"
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, "reviews/400-debug.html")

        settings.DEBUG = False
        response = self.client.post("/post/", data)
        self.assertEqual(response.status_code, 400)
        self.assertTemplateNotUsed(response, "reviews/400-debug.html")

        settings.DEBUG = olddebug

    def testCreateValidReview(self):
        address = "1.2.3.4"
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.post("/post/", data, REMOTE_ADDR=address)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)
        r = Review.objects.first()
        self.assertEqual(r.ip_address, address)
        self.assertEqual(r.rating, 4)
        self.assertEqual(r.comment, "This is my comment")

    def testCreateValidReviewIPv6(self):
        """
        Test creating a valid review with a long IPv6 address.
        Note that this test should fail when Review.ip_address is an IPAddress instead of a GenericIPAddress,
        but does not do so on SQLite or PostgreSQL, because they use the TEXT and INET types, which already
        allow storing an IPv6 address internally.
        """
        address = "2a02::223:6cff:fe8a:2e8a"
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.post("/post/", data, REMOTE_ADDR=address)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)
        r = Review.objects.first()
        self.assertEqual(r.ip_address, address)
        self.assertEqual(r.rating, 4)
        self.assertEqual(r.comment, "This is my comment")

    def testCreateValidCommentNoIP(self):
        """Empty REMOTE_ADDR value should always set a null ip_address value."""
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        for address in ('', None, b''):
            self.client.post("/post/", data, REMOTE_ADDR=address)
            r = Review.objects.last()
            self.assertEqual(r.ip_address, None)

    def testCreateValidReviewIPv6Unpack(self):
        address = "::ffff:18.52.18.52"
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.post("/post/", data, REMOTE_ADDR=address)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)
        r = Review.objects.first()
        # We trim the '::ffff:' bit off because it is an IPv4 addr
        self.assertEqual(r.ip_address, address[7:])
        self.assertEqual(r.rating, 4)
        self.assertEqual(r.comment, "This is my comment")

    @override_settings(REVIEW_APP='api_reviews')
    def testCreateReviewForCustomSite(self):
        """Review site is determined by get_review_site_id hook"""
        Site.objects.create(id=2, domain='api.example.com', name='api')
        a = Article.objects.get(pk=1)
        response = self.client.post("/post/", self.getValidData(a))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.get().site_id, 2)

    def testPostAsAuthenticatedUser(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/post/", data, REMOTE_ADDR="1.2.3.4")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)
        r = Review.objects.first()
        self.assertEqual(r.ip_address, "1.2.3.4")
        u = User.objects.get(username='normaluser')
        self.assertEqual(r.user, u)

    def testPostGoneReview(self):
        """The id of a review that does not exist is a bad request"""
        a = Article.objects.get(pk=1)
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/post/", dict(self.getValidData(a), id="999"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.count(), 0)

    def testPostReviewOfOtherObject(self):
        """The id of the user's review of another object is a bad request"""
        u = User.objects.get(username="normaluser")
        other = Review.objects.create(content_type=CT(Product), object_pk="1", user=u, rating=3, comment="Product",
                                      site_id=settings.SITE_ID, submit_date=timezone.now())
        a = Article.objects.get(pk=1)
        self.client.login(username="normaluser", password="normaluser")
        response = self.client.post("/post/", dict(self.getValidData(a), id=str(other.pk)))
        self.assertEqual(response.status_code, 400)
        other.refresh_from_db()
        self.assertEqual(other.comment, "Product")

    def testPostTwiceUpdatesReview(self):
        """A user has one review of an object, posting another one updates it"""
        a = Article.objects.get(pk=1)
        self.client.login(username="normaluser", password="normaluser")
        self.client.post("/post/", self.getValidData(a))
        r = Review.objects.get()
        r.is_public = True
        r.save()
        response = self.client.post("/post/", dict(self.getValidData(a), rating="2", comment="My second comment."))
        self.assertEqual(response.status_code, 302)
        updated = Review.objects.get()
        self.assertEqual(updated.pk, r.pk)
        self.assertEqual(updated.rating, 2)
        self.assertEqual(updated.comment, "My second comment.")
        self.assertFalse(updated.is_public)

    def testPostTwiceAnonymously(self):
        """Anonymous reviews belong to nobody, so each post adds one"""
        a = Article.objects.get(pk=1)
        self.client.post("/post/", self.getValidData(a))
        self.client.post("/post/", dict(self.getValidData(a), comment="My second comment."))
        self.assertEqual(Review.objects.count(), 2)

    def testPostUpdatesLatestDuplicate(self):
        """Duplicates posted by earlier versions remain, the latest one is updated"""
        a = Article.objects.get(pk=1)
        u = User.objects.get(username="normaluser")
        old, new = [
            Review.objects.create(content_type=CT(Article), object_pk="1", user=u, rating=3, comment=comment,
                                  site_id=settings.SITE_ID, submit_date=timezone.now() - timedelta(days=days))
            for comment, days in (("Old", 2), ("New", 1))
        ]
        self.client.login(username="normaluser", password="normaluser")
        self.client.post("/post/", self.getValidData(a))
        self.assertEqual(Review.objects.count(), 2)
        old.refresh_from_db()
        new.refresh_from_db()
        self.assertEqual(old.comment, "Old")
        self.assertEqual(new.comment, "This is my comment")

    @override_settings(REVIEW_APP='api_reviews')
    def testPostOnOtherSiteAddsReview(self):
        """The review of an object on another site is a separate one"""
        Site.objects.create(id=2, domain='api.example.com', name='api')
        a = Article.objects.get(pk=1)
        u = User.objects.get(username="normaluser")
        Review.objects.create(content_type=CT(Article), object_pk="1", user=u, rating=3, comment="Site 1",
                              site_id=settings.SITE_ID, submit_date=timezone.now())
        self.client.login(username="normaluser", password="normaluser")
        self.client.post("/post/", self.getValidData(a))
        self.assertEqual(list(Review.objects.order_by('site_id').values_list('site_id', 'comment')),
                         [(1, "Site 1"), (2, "This is my comment")])

    def testReviewSignals(self):
        """Test signals emitted by the review posting view"""

        # callback
        def receive(sender, **kwargs):
            self.assertEqual(kwargs['review'].comment, "This is my comment")
            self.assertTrue('request' in kwargs)
            received_signals.append(kwargs.get('signal'))

        # Connect signals and keep track of handled ones
        received_signals = []
        expected_signals = [
            signals.review_was_posted
        ]
        for signal in expected_signals:
            signal.connect(receive)

        # Post a comment and check the signals
        self.testCreateValidReview()
        self.assertEqual(received_signals, expected_signals)

        for signal in expected_signals:
            signal.disconnect(receive)

    def testReviewNext(self):
        """Test the different "next" actions the review view can take"""
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.post("/post/", data)
        self.assertRedirects(
            response,
            '/posted/?r=%s' % Review.objects.latest('id').pk,
            fetch_redirect_response=False,
        )
        data["next"] = "/somewhere/else/"
        data["comment"] = "This is another review"
        response = self.client.post("/post/", data)
        self.assertRedirects(
            response,
            '/somewhere/else/?r=%s' % Review.objects.latest('id').pk,
            fetch_redirect_response=False,
        )
        data["next"] = "http://badserver/somewhere/else/"
        data["comment"] = "This is another review with an unsafe next url"
        response = self.client.post("/post/", data)
        self.assertRedirects(
            response,
            '/posted/?r=%s' % Review.objects.latest('id').pk,
            fetch_redirect_response=False,
        )

    def testReviewDoneView(self):
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        response = self.client.post("/post/", data)
        review = Review.objects.latest('id')
        location = '/posted/?r=%s' % review.pk
        self.assertRedirects(response, location, fetch_redirect_response=False)
        response = self.client.get(location)
        self.assertTemplateUsed(response, "reviews/posted.html")
        self.assertEqual(response.context["review"], review)

    def testReviewNextWithQueryString(self):
        """
        The `next` key needs to handle already having a query string.
        """
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["next"] = "/somewhere/else/?foo=bar"
        data["comment"] = "This is another review"
        response = self.client.post("/post/", data)
        self.assertRedirects(
            response,
            '/somewhere/else/?foo=bar&r=%s' % Review.objects.latest('id').pk,
            fetch_redirect_response=False,
        )

    def testReviewPostRedirectWithInvalidIntegerPK(self):
        """
        Tests that attempting to retrieve the location specified in the
        post redirect, after adding some invalid data to the expected
        querystring it ends with, doesn't cause a server error.
        """
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["comment"] = "This is another review"
        response = self.client.post("/post/", data)
        location = response["Location"]
        broken_location = location + "\ufffd"
        response = self.client.get(broken_location)
        self.assertEqual(response.status_code, 200)

    def testReviewNextWithQueryStringAndAnchor(self):
        """
        The `next` key needs to handle already having an anchor.
        """
        # With a query string also.
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["next"] = "/somewhere/else/?foo=bar#baz"
        data["comment"] = "This is another review"
        response = self.client.post("/post/", data)
        self.assertRedirects(
            response,
            '/somewhere/else/?foo=bar&r=%s#baz' % Review.objects.latest('id').pk,
            fetch_redirect_response=False,
        )

        # Without a query string
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        data["next"] = "/somewhere/else/#baz"
        data["comment"] = "This is another review"
        response = self.client.post("/post/", data)
        self.assertRedirects(
            response,
            '/somewhere/else/?r=%s#baz' % Review.objects.latest('id').pk,
            fetch_redirect_response=False,
        )
