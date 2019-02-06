from __future__ import absolute_import

from reviews.models import Review

from . import ReviewTestCase
from testapp.models import Article, Product


class ReviewModelTests(ReviewTestCase):
    def testSave(self):
        for c in self.createSomeReviews():
            self.assertNotEqual(c.submit_date, None)

    def testUserProperties(self):
        r1, r2, r3, r4 = self.createSomeReviews()
        self.assertEqual(r1.user.first_name, "Frank")
        self.assertEqual(r2.rating, '4')
        self.assertEqual(r2.user, r3.user)
        self.assertEqual(r4.content_object, Product.objects.get(pk=2))
