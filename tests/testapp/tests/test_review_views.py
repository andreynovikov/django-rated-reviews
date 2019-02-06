from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth.models import User

from reviews import signals
from reviews.models import REVIEW_MAX_LENGTH, Review

from . import ReviewTestCase
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

    '''
    def testPreventDuplicateReviews(self):
        """Prevent posting the reviews twice by one user"""
        a = Article.objects.get(pk=1)
        data = self.getValidData(a)
        self.client.post("/post/", data)
        self.client.post("/post/", dict(data, comment="My second comment."))
        self.assertEqual(Review.objects.count(), 1)
    '''

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
