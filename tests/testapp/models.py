"""
Reviews may be attached to any object. See the review documentation for
more information.
"""

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100)
    body = models.TextField()
    pub_date = models.DateField()

    def __str__(self):
        return self.headline


@python_2_unicode_compatible
class Product(models.Model):
    title = models.CharField(max_length=250)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    enable_reviews = models.BooleanField(default=True)

    def __str__(self):
        return self.title
