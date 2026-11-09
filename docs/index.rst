===========================
Django Rated Reviews
===========================

.. module:: reviews
   :synopsis: Rated reviews for Django.

.. highlight:: html+django

Rated reviews is derived from `Django “excontrib” Comments <https://github.com/django/django-contrib-comments/>`_ and can be used to attach reviews with rating to any model. The core difference from comments is that user can provide only one review per item. Rating is expressed by a number and by default visualized with stars. However, it can be changed to whatever you want. Rating grades are also configurable.

Optionally rating can be weighted. For instance, you can designate experts whose rating would be more valuable. Alternatively, add weight to reviews of real byers of sold product.

Reviews can be used with Django templates or through optional :doc:`REST API <api>`.

Requirements
================

* Python 3.10+
* Django 5.2+ (5.2, 6.0 and 6.1 are tested)
* ``django.contrib.sites`` framework
* Optional: `Django REST framework <https://www.django-rest-framework.org/>`_ 3.16+ for REST API

Contents
================

.. toctree::
   :maxdepth: 2

   quickstart
   settings
   templatetags
   api
   models
