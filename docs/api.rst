========
REST API
========

.. versionadded:: 2.0

Besides template tags, reviews can be listed, posted and modified with REST API.
It is useful for single page applications, mobile applications and sites that
are rendered by a separate frontend.

REST API is optional and is built with `Django REST framework`_. The rest of
the reviews app does not depend on it.

Installation
============

#. Install the reviews app together with Django REST framework::

       pip install "django-rated-reviews[api]"

#. Add ``'rest_framework'`` to ``INSTALLED_APPS``.

#. Register :class:`~reviews.api.ReviewViewSet` in a router in your project's
   ``urls.py``:

   .. code-block:: python

        from django.urls import include, path
        from rest_framework.routers import DefaultRouter

        from reviews.api import ReviewViewSet

        router = DefaultRouter()
        router.register(r'reviews', ReviewViewSet, basename='review')
        router.register(r'reviews/(?P<model>\w+\.\w+)/(?P<identifier>[^/.]+)', ReviewViewSet, basename='model-review')

        urlpatterns = [
            ...
            path('api/', include(router.urls)),
            ...
        ]

Authentication, renderers and other API policies are configured with the
``REST_FRAMEWORK`` setting, as usual for Django REST framework.

Reviewed objects
================

Reviewed model is referenced as ``app_label.model_name`` (lower-cased model
name, e.g. ``shop.product``) and reviewed object by its primary key. Both can
be passed in URL, as registered above, or as ``model`` and ``identifier`` query
parameters. These requests are the same::

    GET /api/reviews/shop.product/17/
    GET /api/reviews/?model=shop.product&identifier=17

Model is always required. Without an identifier the API lists reviews of all
objects of the model.

Endpoints
=========

In the table below ``{model}`` is ``app_label.model_name``, ``{identifier}``
is the primary key of reviewed object and ``{id}`` is the primary key of a
review.

.. list-table::
   :header-rows: 1
   :widths: 10 40 35 15

   * - Method
     - URL
     - Description
     - Permission
   * - ``GET``
     - ``/api/reviews/{model}/{identifier}/``
     - :ref:`Published reviews of an object <api-list>`
     - Anyone
   * - ``POST``
     - ``/api/reviews/{model}/{identifier}/``
     - :ref:`Post a review <api-post>`
     - Authenticated user
   * - ``GET``
     - ``/api/reviews/{model}/{identifier}/{id}/``
     - Get a review
     - Anyone
   * - ``PUT``
     - ``/api/reviews/{model}/{identifier}/{id}/``
     - :ref:`Modify a review <api-modify>`
     - Review author
   * - ``DELETE``
     - ``/api/reviews/{model}/{identifier}/{id}/``
     - Delete a review
     - Staff
   * - ``GET``
     - ``/api/reviews/{model}/{identifier}/average/``
     - :ref:`Weighted average rating <api-average>`
     - Anyone
   * - ``GET``
     - ``/api/reviews/{model}/{identifier}/form/``
     - :ref:`Review form description <api-post>`
     - Anyone
   * - ``GET``
     - ``/api/reviews/?model={model}``
     - Published reviews of all objects of a model
     - Anyone

Reviews are always limited to the current site, see
:func:`~reviews.get_review_site_id`.

.. _api-list:

Listing reviews
===============

Only published reviews are listed. If ``REVIEW_PUBLISH_UNMODERATED`` is
``False`` (default), reviews are published when they are approved in admin.

Review list of an object also contains:

``statistics``
    Weighted average rating (``value``), its text and number of reviews for
    each rating. It is present only if the object has published reviews.

``user_reviews``
    Identifiers of reviews of the authenticated user for the object, including
    reviews that are not yet published. Use it to show user's own review or to
    let user modify it instead of posting a new one.

Example::

    GET /api/reviews/shop.product/17/

.. code-block:: json

    {
      "count": 3,
      "next": null,
      "previous": null,
      "results": [
        {
          "id": 3,
          "comment": "Does the job",
          "rating": {"value": 4, "text": "Very Good"},
          "weight": 1,
          "submit_date": "2026-11-09T10:36:10.007673Z",
          "is_public": true,
          "user": null,
          "site": 1
        },
        {
          "id": 2,
          "comment": "Good, but a bit heavy",
          "rating": {"value": 4, "text": "Very Good"},
          "weight": 1,
          "submit_date": "2026-11-09T10:36:10.007381Z",
          "is_public": true,
          "user": {"id": 102, "name": "mary"},
          "site": 1
        },
        {
          "id": 1,
          "comment": "Very nice and handy",
          "rating": {"value": 5, "text": "Excellent"},
          "weight": 1,
          "submit_date": "2026-11-09T10:36:10.006841Z",
          "is_public": true,
          "user": {"id": 101, "name": "john"},
          "site": 1
        }
      ],
      "statistics": {
        "value": 4.333333333333333,
        "text": "Very Good",
        "ratings": [
          {"rating": 4, "count": 2},
          {"rating": 5, "count": 1}
        ]
      },
      "user_reviews": [1]
    }

Rating is represented by its value and text, see
:func:`~reviews.get_review_rating_text`. Review author is represented by its
primary key and its string representation, the same as in templates. Other user
data is not exposed, provide :func:`~reviews.get_review_api_user_serializer`
to change it. ``user`` is ``null`` for anonymous reviews. IP address and content
type are never exposed. Object identifier (``object_pk``) is included only when
reviews of all objects of a model are listed.

Pagination
----------

Lists are paginated with :class:`~reviews.api.ReviewPagination`: 20 reviews per
page, which can be changed with the ``page_size`` query parameter (up to 1000).
Use ``page`` query parameter to get other pages. Pagination class can be changed
with :func:`~reviews.get_review_api_pagination_class`. Statistics are calculated
for all reviews, not only for the current page.

Filtering
---------

Reviews can be filtered by fields of the review model, except IP address and
content type. Repeat the parameter to filter by several values::

    GET /api/reviews/shop.product/17/?rating=5
    GET /api/reviews/shop.product/17/?rating=4&rating=5
    GET /api/reviews/?model=shop.product&user=12

Statistics in the response are calculated for the filtered reviews.

.. _api-average:

Average rating
==============

Weighted average rating of published reviews, its text and number of reviews::

    GET /api/reviews/shop.product/17/average/

.. code-block:: json

    {
      "value": 4.333333333333333,
      "text": "Very Good",
      "count": 3
    }

If there are no reviews, only ``count`` is returned:

.. code-block:: json

    {"count": 0}

.. _api-post:

Posting a review
================

Posting a review requires an authenticated user. Review data is validated by
the review form, exactly as when it is posted by the HTML form (see
:ref:`notes-on-the-review-form`). So a review is posted in two steps.

First, get the form description. It contains the fields that should be shown
to user and the values of hidden security fields::

    GET /api/reviews/shop.product/17/form/

.. code-block:: json

    [
      {
        "name": "content_type", "label": "Content type", "id": "id_content_type", "help": "",
        "class": "CharField", "widget": "HiddenInput", "required": true,
        "value": "shop.product"
      },
      {
        "name": "object_pk", "label": "Object pk", "id": "id_object_pk", "help": "",
        "class": "CharField", "widget": "HiddenInput", "required": true,
        "value": "17"
      },
      {
        "name": "timestamp", "label": "Timestamp", "id": "id_timestamp", "help": "",
        "class": "IntegerField", "widget": "HiddenInput", "required": true,
        "value": "1794220570"
      },
      {
        "name": "security_hash", "label": "Security hash", "id": "id_security_hash", "help": "",
        "class": "CharField", "widget": "HiddenInput", "required": true,
        "value": "10b4b755bd5e9a86ec3639acd2fcaa1bd50e0138"
      },
      {
        "name": "rating", "label": "Rating", "id": "id_rating", "help": "",
        "class": "IntegerField", "widget": "Select", "required": true,
        "choices": [
          ["", "Select a rating"], ["1", "Terrible"], ["2", "Poor"],
          ["3", "Average"], ["4", "Very Good"], ["5", "Excellent"]
        ],
        "attrs": {"class": "star-rating"}
      },
      {
        "name": "comment", "label": "Comment", "id": "id_comment", "help": "",
        "class": "CharField", "widget": "Textarea", "required": true,
        "attrs": {"cols": "40", "rows": "10", "maxlength": "3000"}
      },
      {
        "name": "honeypot", "label": "", "id": "id_honeypot", "help": "",
        "class": "CharField", "widget": "TextInput", "required": false,
        "attrs": {"style": "display:none"}
      }
    ]

Then post the values of all fields. Hidden fields must be sent unchanged and
``honeypot`` must be left empty::

    POST /api/reviews/shop.product/17/
    Content-Type: application/json

.. code-block:: json

    {
      "content_type": "shop.product",
      "object_pk": "17",
      "timestamp": "1794220570",
      "security_hash": "10b4b755bd5e9a86ec3639acd2fcaa1bd50e0138",
      "rating": "5",
      "comment": "Excellent box",
      "honeypot": ""
    }

The response (``201 Created``) contains the new review. Unless
``REVIEW_PUBLISH_UNMODERATED`` is ``True``, it is not published until it is
approved in admin, but it is listed in ``user_reviews`` of the review list.

.. code-block:: json

    {
      "id": 4,
      "comment": "Excellent box",
      "rating": {"value": 5, "text": "Excellent"},
      "weight": 1,
      "submit_date": "2026-11-09T10:36:10.152069Z",
      "is_public": false,
      "user": {"id": 101, "name": "john"},
      "site": 1
    }

Security hash expires after ``REVIEW_COMPOSE_TIMEOUT`` seconds (2 hours by
default), get the form again if user spends more time writing a review.

Invalid data is rejected with ``400 Bad Request`` and form errors:

.. code-block:: json

    {
      "rating": ["This field is required."]
    }

As with the HTML form, the review is saved with the current user, IP address,
site (see :func:`~reviews.get_review_site_id`) and rating weight (see
:func:`~reviews.get_review_user_weight`), and
``reviews.signals.review_was_posted`` signal is sent.

.. _api-modify:

Modifying a review
==================

Review author can modify the review with ``PUT`` request to the review URL. The
request requires the same data as posting a review, including fresh values of
security fields::

    PUT /api/reviews/shop.product/17/4/

Modified review is considered unmoderated again, rating weight and IP address
are updated and ``review_was_posted`` signal is sent.

Errors
======

``400 Bad Request``
    Model is missing or does not exist, object identifier is missing where it
    is required, filter value is invalid or review data is invalid.

``403 Forbidden``
    Anonymous user posts a review, user modifies a review of another user or
    non-staff user deletes a review.

``404 Not Found``
    Reviewed object or review does not exist.

Customization
=============

Besides the settings that apply to all reviews (see :doc:`settings`), the
following functions of a custom reviews app (``REVIEW_APP``) customize the API:

* :func:`~reviews.get_review_api_user_serializer` -- representation of review
  author;
* :func:`~reviews.get_review_api_pagination_class` -- pagination of review lists
  and its response format;
* :func:`~reviews.get_review_site_id` -- site of reviews, e.g. when it is
  determined by a custom middleware;
* :func:`~reviews.get_review_rating_text` -- text of ratings and average ratings;
* :func:`~reviews.get_review_user_weight` -- rating weight of posted reviews.

For example, to use the response format and user representation of an existing
API:

.. code-block:: python

    # myreviews/__init__.py

    def get_review_api_user_serializer():
        from myproject.serializers import UserListSerializer
        return UserListSerializer


    def get_review_api_pagination_class():
        from myproject.api import StandardResultsSetPagination
        return StandardResultsSetPagination

:class:`~reviews.api.ReviewViewSet` can also be subclassed, e.g. to change
URL keyword arguments (``model_url_kwarg``, ``identifier_url_kwarg``) or
permissions (``get_permissions()``).

Reference
=========

.. autoclass:: reviews.api.ReviewViewSet
   :members: list, average, form

.. autoclass:: reviews.api.ReviewSerializer

.. autoclass:: reviews.api.ReviewActionSerializer

.. autoclass:: reviews.api.UserSerializer

.. autoclass:: reviews.api.ReviewPagination

.. autoclass:: reviews.api.IsOwner

.. _Django REST framework: https://www.django-rest-framework.org/
