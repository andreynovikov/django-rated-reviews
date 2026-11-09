"""
REST API tests. They run only if Django REST framework is installed.
"""
import time
from importlib.util import find_spec
from unittest import skipUnless

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test.utils import override_settings

from reviews import signals
from reviews.admin import ReviewAdmin
from reviews.forms import ReviewForm
from reviews.models import Review

from testapp.models import Article, Product

from . import CT, ReviewTestCase


HAS_DRF = find_spec('rest_framework') is not None


def object_url(target, suffix=''):
    """
    URL of reviews of a particular object, e.g. /api/reviews/testapp.product/1/average/
    """
    return '/api/reviews/{}.{}/{}/{}'.format(target._meta.app_label, target._meta.model_name, target.pk, suffix)


@skipUnless(HAS_DRF, "Django REST framework is not installed")
@override_settings(ROOT_URLCONF='testapp.urls_api')
class ReviewAPITestCase(ReviewTestCase):

    def setUp(self):
        super().setUp()
        self.product = Product.objects.get(pk=1)
        self.other_product = Product.objects.get(pk=2)
        self.article = Article.objects.get(pk=1)
        self.user = User.objects.get(username='normaluser')
        self.author = User.objects.create(username='author', first_name='Ann', last_name='Author',
                                          email='ann@example.com')
        self.staff = User.objects.create(username='staff', is_staff=True)

    def review(self, target, rating, user=None, is_public=True, weight=1, site_id=1, **kwargs):
        return Review.objects.create(
            content_type=CT(target),
            object_pk=str(target.pk),
            rating=rating,
            weight=weight,
            user=user,
            comment=kwargs.pop('comment', 'Review'),
            site_id=site_id,
            is_public=is_public,
            **kwargs
        )

    def get(self, url, **kwargs):
        response = self.client.get(url, **kwargs)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def post(self, url, data, **kwargs):
        return self.client.post(url, data, content_type='application/json', **kwargs)

    def put(self, url, data, **kwargs):
        return self.client.put(url, data, content_type='application/json', **kwargs)

    def connect_signal(self):
        """
        Returns list that collects reviews sent with review_was_posted signal.
        """
        received = []

        def receiver(sender, review, request, **kwargs):
            received.append(review.pk)

        signals.review_was_posted.connect(receiver)
        self.addCleanup(signals.review_was_posted.disconnect, receiver)
        return received


class ReviewAPIReadTests(ReviewAPITestCase):

    def testListByPath(self):
        r1 = self.review(self.product, 5, user=self.author)
        r2 = self.review(self.product, 3)
        self.review(self.product, 1, is_public=False)
        self.review(self.other_product, 2)
        self.review(self.article, 4)

        data = self.get(object_url(self.product))
        self.assertTrue({'count', 'next', 'previous', 'results'}.issubset(data))
        self.assertEqual(data['count'], 2)
        self.assertEqual({r['id'] for r in data['results']}, {r1.pk, r2.pk})

        review = next(r for r in data['results'] if r['id'] == r1.pk)
        self.assertEqual(review['rating'], {'value': 5, 'text': 'Excellent'})
        self.assertEqual(review['comment'], 'Review')
        self.assertTrue(review['is_public'])
        for field in ('content_type', 'ip_address', 'object_pk'):
            self.assertNotIn(field, review)

        anonymous = next(r for r in data['results'] if r['id'] == r2.pk)
        self.assertIsNone(anonymous['user'])

    def testListByQueryParams(self):
        self.review(self.product, 5, user=self.author)
        self.review(self.product, 3)
        self.review(self.other_product, 2)

        by_path = self.get(object_url(self.product))
        by_params = self.get('/api/reviews/', data={'model': 'testapp.product', 'identifier': self.product.pk})
        self.assertEqual(by_params, by_path)

    def testUserIsNotDisclosed(self):
        self.review(self.product, 5, user=self.author)
        data = self.get(object_url(self.product))
        self.assertEqual(data['results'][0]['user'], {'id': self.author.pk, 'name': 'author'})
        self.assertNotIn(self.author.email, str(data))
        self.assertNotIn(self.author.last_name, str(data))

    def testListStatistics(self):
        self.review(self.product, 5, weight=3)
        self.review(self.product, 1, weight=1)
        self.review(self.product, 2, weight=10, is_public=False)

        statistics = self.get(object_url(self.product))['statistics']
        # (5 * 3 + 1 * 1) / (3 + 1)
        self.assertAlmostEqual(statistics['value'], 4.0)
        self.assertEqual(statistics['text'], 'Very Good')
        self.assertEqual(statistics['ratings'], [{'rating': 1, 'count': 1}, {'rating': 5, 'count': 1}])

    def testListWithoutReviews(self):
        self.review(self.product, 2, is_public=False)
        data = self.get(object_url(self.product))
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])
        self.assertNotIn('statistics', data)

    def testListUserReviews(self):
        public = self.review(self.product, 5, user=self.user)
        pending = self.review(self.product, 2, user=self.user, is_public=False)
        self.review(self.product, 4, user=self.author)
        self.review(self.other_product, 4, user=self.user)

        self.assertNotIn('user_reviews', self.get(object_url(self.product)))

        self.client.force_login(self.user)
        data = self.get(object_url(self.product))
        self.assertEqual(sorted(data['user_reviews']), sorted([public.pk, pending.pk]))
        # Pending review is not listed publicly even to its author
        self.assertNotIn(pending.pk, [r['id'] for r in data['results']])

    def testListForModel(self):
        r1 = self.review(self.product, 5)
        r2 = self.review(self.other_product, 3)
        self.review(self.other_product, 1, is_public=False)
        self.review(self.article, 4)

        data = self.get('/api/reviews/', data={'model': 'testapp.product'})
        self.assertEqual({r['id'] for r in data['results']}, {r1.pk, r2.pk})
        # Objects are different, so object_pk is included
        self.assertEqual({r['object_pk'] for r in data['results']}, {'1', '2'})
        self.assertNotIn('statistics', data)
        self.assertNotIn('user_reviews', data)

    def testFilterByField(self):
        r3 = self.review(self.product, 3, user=self.author)
        r4 = self.review(self.product, 4, ip_address='1.2.3.4')
        r5 = self.review(self.product, 5, ip_address='5.6.7.8')
        url = object_url(self.product)

        data = self.get(url, data={'rating': 4})
        self.assertEqual([r['id'] for r in data['results']], [r4.pk])
        self.assertEqual(data['statistics']['ratings'], [{'rating': 4, 'count': 1}])

        data = self.get(url + '?rating=3&rating=4')
        self.assertEqual({r['id'] for r in data['results']}, {r3.pk, r4.pk})

        data = self.get(url, data={'user': self.author.pk})
        self.assertEqual([r['id'] for r in data['results']], [r3.pk])

        # Unknown and private fields are ignored
        data = self.get(url, data={'unknown': 'value', 'ip_address': '1.2.3.4'})
        self.assertEqual({r['id'] for r in data['results']}, {r3.pk, r4.pk, r5.pk})

    def testFilterByIncorrectValue(self):
        self.review(self.product, 3)
        response = self.client.get(object_url(self.product), data={'rating': 'abc'})
        self.assertEqual(response.status_code, 400)

    def testSiteIsolation(self):
        Site.objects.create(id=2, domain='other.example.com', name='other')
        r1 = self.review(self.product, 5)
        self.review(self.product, 1, site_id=2)

        data = self.get(object_url(self.product))
        self.assertEqual([r['id'] for r in data['results']], [r1.pk])
        self.assertEqual(data['statistics']['value'], 5.0)
        self.assertEqual(self.get(object_url(self.product, 'average/'))['count'], 1)

    def testPagination(self):
        for i in range(21):
            self.review(self.product, 4)
        url = object_url(self.product)

        data = self.get(url)
        self.assertEqual(data['count'], 21)
        self.assertEqual(len(data['results']), 20)
        self.assertIsNotNone(data['next'])
        self.assertIsNone(data['previous'])

        data = self.get(url, data={'page_size': 5, 'page': 5})
        self.assertEqual(len(data['results']), 1)
        self.assertIsNone(data['next'])

        data = self.get(url, data={'page_size': 100000})
        self.assertEqual(len(data['results']), 21)
        # Statistics are calculated for all reviews, not for one page
        self.assertEqual(self.get(url, data={'page_size': 5})['statistics']['ratings'], [{'rating': 4, 'count': 21}])

    def testRetrieve(self):
        review = self.review(self.product, 4, user=self.author)
        data = self.get(object_url(self.product, '{}/'.format(review.pk)))
        self.assertEqual(data['id'], review.pk)
        self.assertEqual(data['rating'], {'value': 4, 'text': 'Very Good'})
        self.assertEqual(data['user'], {'id': self.author.pk, 'name': 'author'})

    def testRetrieveFromAnotherObject(self):
        review = self.review(self.product, 4)
        response = self.client.get(object_url(self.other_product, '{}/'.format(review.pk)))
        self.assertEqual(response.status_code, 404)

    def testAverage(self):
        self.review(self.product, 5, weight=3)
        self.review(self.product, 1, weight=1)
        self.review(self.product, 1, weight=10, is_public=False)

        data = self.get(object_url(self.product, 'average/'))
        self.assertAlmostEqual(data['value'], 4.0)
        self.assertEqual(data['text'], 'Very Good')
        self.assertEqual(data['count'], 2)

        by_params = self.get('/api/reviews/average/', data={'model': 'testapp.product', 'identifier': 1})
        self.assertEqual(by_params, data)

    def testAverageWithoutReviews(self):
        self.assertEqual(self.get(object_url(self.product, 'average/')), {'count': 0})

    def testForm(self):
        data = self.get(object_url(self.product, 'form/'))
        fields = {f['name']: f for f in data}
        self.assertEqual(list(fields), ['content_type', 'object_pk', 'timestamp', 'security_hash',
                                        'rating', 'comment', 'honeypot'])

        self.assertEqual(fields['content_type']['value'], 'testapp.product')
        self.assertEqual(fields['object_pk']['value'], '1')
        self.assertEqual(fields['security_hash']['widget'], 'HiddenInput')
        self.assertEqual(len(fields['security_hash']['value']), 40)

        rating = fields['rating']
        self.assertEqual(rating['label'], 'Rating')
        self.assertTrue(rating['required'])
        self.assertEqual(rating['widget'], 'Select')
        self.assertEqual(rating['attrs'], {'class': 'star-rating'})
        self.assertEqual(rating['choices'][0], ['', 'Select a rating'])
        self.assertEqual(rating['choices'][-1], ['5', 'Excellent'])

        self.assertTrue(fields['comment']['required'])
        self.assertFalse(fields['honeypot']['required'])

    def testFormUnknownObject(self):
        response = self.client.get('/api/reviews/testapp.product/999/form/')
        self.assertEqual(response.status_code, 404)
        response = self.client.get('/api/reviews/testapp.product/abc/form/')
        self.assertEqual(response.status_code, 404)


class ReviewAPIWriteTests(ReviewAPITestCase):

    def testCreateRequiresLogin(self):
        response = self.post(object_url(self.product), self.getValidData(self.product))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Review.objects.count(), 0)

    def testCreate(self):
        received = self.connect_signal()
        self.client.force_login(self.user)
        response = self.post(object_url(self.product), self.getValidData(self.product), REMOTE_ADDR='1.2.3.4')
        self.assertEqual(response.status_code, 201, response.content)

        review = Review.objects.get()
        self.assertEqual(review.content_object, self.product)
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.site_id, 1)
        self.assertEqual(review.ip_address, '1.2.3.4')
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, 'This is my comment')
        self.assertEqual(review.weight, 1)
        self.assertFalse(review.is_public)
        self.assertEqual(received, [review.pk])

        data = response.json()
        self.assertEqual(data['id'], review.pk)
        self.assertEqual(data['rating'], {'value': 4, 'text': 'Very Good'})
        self.assertEqual(data['comment'], 'This is my comment')
        self.assertEqual(data['user'], {'id': self.user.pk, 'name': 'normaluser'})
        self.assertNotIn('ip_address', data)

    def testCreateByQueryParams(self):
        self.client.force_login(self.user)
        response = self.post('/api/reviews/?model=testapp.product&identifier=1', self.getValidData(self.product))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Review.objects.get().content_object, self.product)

    def testCreateInvalid(self):
        form = ReviewForm(self.product)
        expired = int(time.time()) - 3 * 60 * 60
        cases = {
            'tampered hash': {'security_hash': 'x' * 40},
            'expired timestamp': {'timestamp': str(expired), 'security_hash': form.initial_security_hash(expired)},
            'spoofed object': {'object_pk': '2'},
            'rating out of range': {'rating': '9'},
            'missing rating': {'rating': ''},
            'empty comment': {'comment': ''},
            'honeypot': {'honeypot': 'I am a bot'},
        }
        self.client.force_login(self.user)
        for case, changes in cases.items():
            with self.subTest(case):
                data = self.getValidData(self.product)
                data.update(changes)
                response = self.post(object_url(self.product), data)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(Review.objects.count(), 0)

    def testCreateForUnknownObject(self):
        self.client.force_login(self.user)
        response = self.post('/api/reviews/testapp.product/999/', self.getValidData(self.product))
        self.assertEqual(response.status_code, 404)

    def testCreateWithoutObject(self):
        self.client.force_login(self.user)
        response = self.post('/api/reviews/?model=testapp.product', self.getValidData(self.product))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.count(), 0)

    def testUpdateByOwner(self):
        review = self.review(self.product, 2, user=self.user, comment='Old comment')
        received = self.connect_signal()
        self.client.force_login(self.user)
        data = self.getValidData(self.product)
        data.update(rating='5', comment='New comment')
        response = self.put(object_url(self.product, '{}/'.format(review.pk)), data)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['rating'], {'value': 5, 'text': 'Excellent'})

        review.refresh_from_db()
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, 'New comment')
        # Modified review has to be moderated again
        self.assertFalse(review.is_public)
        self.assertEqual(received, [review.pk])
        self.assertEqual(Review.objects.count(), 1)

    def testUpdateByAnotherUser(self):
        review = self.review(self.product, 2, user=self.author, comment='Old comment')
        data = self.getValidData(self.product)
        data.update(rating='5', comment='New comment')
        url = object_url(self.product, '{}/'.format(review.pk))

        response = self.put(url, data)
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.user)
        response = self.put(url, data)
        self.assertEqual(response.status_code, 403)

        review.refresh_from_db()
        self.assertEqual(review.rating, 2)
        self.assertEqual(review.comment, 'Old comment')

    def testDestroy(self):
        review = self.review(self.product, 2, user=self.user)
        url = object_url(self.product, '{}/'.format(review.pk))

        self.assertEqual(self.client.delete(url).status_code, 403)
        self.client.force_login(self.user)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())

        self.client.force_login(self.staff)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def testPostModerateList(self):
        url = object_url(self.product)
        self.client.force_login(self.user)
        response = self.post(url, self.getValidData(self.product))
        self.assertEqual(response.status_code, 201, response.content)
        review_id = response.json()['id']

        data = self.get(url)
        self.assertEqual(data['user_reviews'], [review_id])
        self.assertEqual(data['results'], [])
        self.assertNotIn('statistics', data)

        ReviewAdmin.perform_approve(Review.objects.get(pk=review_id))

        data = self.get(url)
        self.assertEqual([r['id'] for r in data['results']], [review_id])
        self.assertEqual(data['statistics']['value'], 4.0)
        self.assertEqual(data['user_reviews'], [review_id])


class ReviewAPIErrorTests(ReviewAPITestCase):

    def testIncorrectModel(self):
        urls = (
            '/api/reviews/',
            '/api/reviews/average/',
            '/api/reviews/?model=testapp',
            '/api/reviews/?model=nope.model',
            '/api/reviews/?model=testapp.product.extra',
            '/api/reviews/nope.model/1/',
            '/api/reviews/nope.model/1/average/',
        )
        for url in urls:
            with self.subTest(url):
                self.assertEqual(self.client.get(url).status_code, 400)

    def testMissingIdentifier(self):
        response = self.client.get('/api/reviews/form/', data={'model': 'testapp.product'})
        self.assertEqual(response.status_code, 400)


@override_settings(REVIEW_APP='api_reviews')
class ReviewAPIHookTests(ReviewAPITestCase):
    """
    Customization of API with REVIEW_APP (see tests/api_reviews)
    """

    def setUp(self):
        super().setUp()
        Site.objects.create(id=2, domain='api.example.com', name='api')

    def testUserSerializer(self):
        self.review(self.product, 4, user=self.author, site_id=2)
        data = self.get(object_url(self.product))
        self.assertEqual(data['results'][0]['user'], {'username': 'author', 'full_name': 'Ann Author'})

        self.client.force_login(self.user)
        response = self.post(object_url(self.product), self.getValidData(self.product))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['user'], {'username': 'normaluser', 'full_name': 'Joe Normal'})

    def testPagination(self):
        for rating in (3, 4, 5):
            self.review(self.product, rating, site_id=2)
        data = self.get(object_url(self.product))
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['totalPages'], 2)
        self.assertEqual(data['currentPage'], 1)
        self.assertEqual(data['pageSize'], 2)
        self.assertEqual(len(data['results']), 2)
        self.assertNotIn('next', data)
        # Additional data is still provided
        self.assertEqual(data['statistics']['value'], 4.0)

    def testRatingText(self):
        self.review(self.product, 4, weight=2, site_id=2)
        self.review(self.product, 1, weight=1, site_id=2)
        data = self.get(object_url(self.product))
        self.assertEqual({r['rating']['text'] for r in data['results']}, {'4 of 5', '1 of 5'})
        self.assertEqual(data['statistics']['text'], '3 of 5')
        self.assertEqual(self.get(object_url(self.product, 'average/'))['text'], '3 of 5')

    def testSiteId(self):
        review = self.review(self.product, 4, site_id=2)
        self.review(self.product, 1, site_id=1)
        data = self.get(object_url(self.product))
        self.assertEqual([r['id'] for r in data['results']], [review.pk])

        self.client.force_login(self.user)
        response = self.post(object_url(self.product), self.getValidData(self.product))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Review.objects.get(pk=response.json()['id']).site_id, 2)

    def testUserWeight(self):
        self.client.force_login(self.staff)
        data = self.getValidData(self.product)
        data['rating'] = '5'
        response = self.post(object_url(self.product), data)
        self.assertEqual(response.status_code, 201, response.content)
        review = Review.objects.get(pk=response.json()['id'])
        self.assertEqual(review.weight, 3)

        ReviewAdmin.perform_approve(review)
        self.review(self.product, 1, weight=1, site_id=2)
        # (5 * 3 + 1 * 1) / (3 + 1)
        self.assertEqual(self.get(object_url(self.product, 'average/'))['value'], 4.0)
