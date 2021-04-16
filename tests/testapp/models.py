"""
Reviews may be attached to any object. See the review documentation for
more information.
"""

from django.db import models


class Article(models.Model):
    headline = models.CharField(max_length=100)
    body = models.TextField()
    pub_date = models.DateField()

    def __str__(self):
        return self.headline


class Product(models.Model):
    title = models.CharField(max_length=250)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    enable_reviews = models.BooleanField(default=True)

    def __str__(self):
        return self.title
