from __future__ import absolute_import

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.template import Template, Context
from django.test.client import RequestFactory
from django.test.utils import override_settings

from reviews.forms import ReviewForm
from reviews.models import Review

from testapp.models import Article, Product
from . import ReviewTestCase


class ReviewTemplateTagTests(ReviewTestCase):

    def setUp(self):
        super(ReviewTemplateTagTests, self).setUp()
        self.site_2 = Site.objects.create(id=settings.SITE_ID + 1,
            domain="testserver", name="testserver")

    def render(self, t, **c):
        ctx = Context(c)
        out = Template(t).render(ctx)
        return ctx, out

    def testReviewFormTarget(self):
        ctx, out = self.render("{% load reviews %}{% review_form_target %}")
        self.assertEqual(out, "/post/")

    def testGetReviewForm(self, tag=None):
        t = "{% load reviews %}" + (tag or "{% get_review_form for testapp.article a.id as form %}")
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertEqual(out, "")
        self.assertTrue(isinstance(ctx["form"], ReviewForm))

    def testGetReviewFormFromLiteral(self):
        self.testGetReviewForm("{% get_review_form for testapp.article 1 as form %}")

    def testGetReviewFormFromObject(self):
        self.testGetReviewForm("{% get_review_form for a as form %}")

    def testWhitespaceInGetReviewFormTag(self):
        self.testGetReviewForm("{% load review_testtags %}{% get_review_form for a|noop:'x y' as form %}")

    def testRenderReviewForm(self, tag=None):
        t = "{% load reviews %}" + (tag or "{% render_review_form for testapp.article a.id %}")
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertTrue(out.strip().startswith("<form action="))
        self.assertTrue(out.strip().endswith("</script>"))

    def testRenderReviewFormFromLiteral(self):
        self.testRenderReviewForm("{% render_review_form for testapp.article 1 %}")

    def testRenderReviewFormFromObject(self):
        self.testRenderReviewForm("{% render_review_form for a %}")

    def testWhitespaceInRenderReviewFormTag(self):
        self.testRenderReviewForm("{% load review_testtags %}{% render_review_form for a|noop:'x y' %}")

    def testRenderReviewFormFromObjectWithQueryCount(self):
        with self.assertNumQueries(1):
            self.testRenderReviewFormFromObject()

    def verifyGetReviewCount(self, tag=None):
        t = "{% load reviews %}" + (tag or "{% get_review_count for testapp.article a.id as rc %}") + "{{ rc }}"
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertEqual(out, "1")

    def testGetReviewCount(self):
        self.createSomeReviews()
        self.moderateSomeReviews()
        self.verifyGetReviewCount("{% get_review_count for testapp.article a.id as rc %}")

    def testGetReviewCountFromLiteral(self):
        self.createSomeReviews()
        self.moderateSomeReviews()
        self.verifyGetReviewCount("{% get_review_count for testapp.article 1 as rc %}")

    def testGetReviewCountFromObject(self):
        self.createSomeReviews()
        self.moderateSomeReviews()
        self.verifyGetReviewCount("{% get_review_count for a as rc %}")

    def testWhitespaceInGetReviewCountTag(self):
        self.createSomeReviews()
        self.moderateSomeReviews()
        self.verifyGetReviewCount("{% load review_testtags %}{% get_review_count for a|noop:'x y' as rc %}")

    def verifyGetReviewList(self, tag=None):
        r1, r2, r3, r4 = Review.objects.all().order_by('id')[:4]
        t = "{% load reviews %}" + (tag or "{% get_review_list for testapp.product p.id as rl %}")
        ctx, out = self.render(t, p=Product.objects.get(pk=2))
        self.assertEqual(out, "")
        self.assertEqual(list(ctx["rl"]), [r4])

    def testGetReviewList(self):
        self.createSomeReviews()
        self.moderateSomeReviews()
        self.verifyGetReviewList("{% get_review_list for testapp.product p.id as rl %}")

    def testGetReviewListFromLiteral(self):
        self.createSomeReviews()
        self.moderateSomeReviews()
        self.verifyGetReviewList("{% get_review_list for testapp.product 2 as rl %}")

    def testGetReviewListFromObject(self):
        self.createSomeReviews()
        self.moderateSomeReviews()
        self.verifyGetReviewList("{% get_review_list for p as rl %}")

    def testWhitespaceInGetReviewListTag(self):
        self.createSomeReviews()
        self.moderateSomeReviews()
        self.verifyGetReviewList("{% load review_testtags %}{% get_review_list for p|noop:'x y' as rl %}")

    def testGetReviewPermalink(self):
        r1, r2, r3, r4 = self.createSomeReviews()
        self.moderateSomeReviews()
        t = "{% load reviews %}{% get_review_list for testapp.product product.id as rl %}"
        t += "{% get_review_permalink rl.0 %}"
        ct = ContentType.objects.get_for_model(Product)
        product = Product.objects.get(pk=2)
        ctx, out = self.render(t, product=product)
        self.assertEqual(out, "/rr/%s/%s/#r%s" % (ct.id, product.id, r4.id))

    def testGetReviewPermalinkFormatted(self):
        r1, r2, r3, r4 = self.createSomeReviews()
        self.moderateSomeReviews()
        t = "{% load reviews %}{% get_review_list for testapp.product product.id as rl %}"
        t += "{% get_review_permalink rl.0 '#r%(id)s-with-%(rating)s' %}"
        ct = ContentType.objects.get_for_model(Product)
        product = Product.objects.get(pk=2)
        ctx, out = self.render(t, product=product)
        self.assertEqual(out, "/rr/%s/%s/#r%s-with-4" % (ct.id, product.id, r4.id))

    def testWhitespaceInGetCommentPermalinkTag(self):
        r1, r2, r3, r4 = self.createSomeReviews()
        self.moderateSomeReviews()
        t = "{% load reviews review_testtags %}{% get_review_list for testapp.product product.id as rl %}"
        t += "{% get_review_permalink rl.0|noop:'x y' %}"
        ct = ContentType.objects.get_for_model(Product)
        product = Product.objects.get(pk=2)
        ctx, out = self.render(t, product=product)
        self.assertEqual(out, "/rr/%s/%s/#r%s" % (ct.id, product.id, r4.id))

    def testRenderReviewList(self, tag=None):
        t = "{% load reviews %}" + (tag or "{% render_review_list for testapp.article a.id %}")
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertTrue(out.strip().startswith("<dl id=\"review-list\">"))
        self.assertTrue(out.strip().endswith("</dl>"))

    def testRenderReviewListFromLiteral(self):
        self.testRenderReviewList("{% render_review_list for testapp.article 1 %}")

    def testRenderReviewListFromObject(self):
        self.testRenderReviewList("{% render_review_list for a %}")

    def testWhitespaceInRenderReviewListTag(self):
        self.testRenderReviewList("{% load review_testtags %}{% render_review_list for a|noop:'x y' %}")

    def testNumberQueries(self):
        """
        Ensure that the template tags use cached content types to reduce the
        number of DB queries.
        """

        self.createSomeReviews()
        self.moderateSomeReviews()

        # {% render_comment_list %} -----------------

        # Clear CT cache
        ContentType.objects.clear_cache()
        with self.assertNumQueries(3):
            self.testRenderReviewListFromObject()

        # CT's should be cached
        with self.assertNumQueries(2):
            self.testRenderReviewListFromObject()

        # {% get_review_list %} --------------------

        ContentType.objects.clear_cache()
        with self.assertNumQueries(4):
            self.verifyGetReviewList()

        with self.assertNumQueries(3):
            self.verifyGetReviewList()

        # {% render_review_form %} -----------------

        ContentType.objects.clear_cache()
        with self.assertNumQueries(3):
            self.testRenderReviewForm()

        with self.assertNumQueries(2):
            self.testRenderReviewForm()

        # {% get_review_form %} --------------------

        ContentType.objects.clear_cache()
        with self.assertNumQueries(3):
            self.testGetReviewForm()

        with self.assertNumQueries(2):
            self.testGetReviewForm()

        # {% get_review_count %} -------------------

        ContentType.objects.clear_cache()
        with self.assertNumQueries(3):
            self.verifyGetReviewCount()

        with self.assertNumQueries(2):
            self.verifyGetReviewCount()
