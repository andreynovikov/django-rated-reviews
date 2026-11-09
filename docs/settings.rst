.. _settings-reviews:

==========================
Settings and customization
==========================

Settings
========

All settings are optional.

``REVIEW_MAX_LENGTH``
    The maximum length of the review comment field, in characters. Comments
    longer than this will be rejected. Defaults to ``3000``.

``REVIEW_PUBLISH_UNMODERATED``
    If ``False`` (default) reviews are not published until they are moderated
    in admin. If user modifies existing review it is considered unmoderated
    again.

``REVIEW_COMPOSE_TIMEOUT``
    The maximum review form timeout in seconds. The default value is
    ``2 * 60 * 60`` (2 hours).

``REVIEW_RATING_CHOICES``
    Custom rating choices, each represented by one star (currently the maximum
    supported number is 10). Default choices are:

    .. code-block:: python

        REVIEW_RATING_CHOICES = (
            ('1', _('Terrible')),
            ('2', _('Poor')),
            ('3', _('Average')),
            ('4', _('Very Good')),
            ('5', _('Excellent')),
        )

``REVIEW_SHOW_RATING_TEXT``
    If ``True`` (default) rating text (as specified by choices) is displayed
    next to rating stars.

``REVIEW_ALLOW_PROFANITIES``
    If ``False`` review comment is checked against words in
    ``PROFANITIES_LIST``. If it contains any of the words, review is rejected.

``REVIEW_ADMIN_LINK_SYMBOL``
    Review admin exposes a link to review on a web site. By default it is shown
    as ``&#9654;`` (▶). It can be changed to any other symbol or text, e.g. if
    Font Awesome is attached to admin the following setting can be used:
    ``'<i class="fas fa-external-link-alt"></i>'``.

``REVIEW_APP``
    Name of a custom reviews app, see below.

Custom reviews app
==================

Behaviour of reviews can be changed by a custom reviews app. Add it to
``INSTALLED_APPS`` and set ``REVIEW_APP`` to its name:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'reviews',
        'myreviews',
        ...
    ]

    REVIEW_APP = 'myreviews'

The app can define any of the functions listed below in its ``__init__.py``.
Functions that are not defined fall back to the default implementation. Reviews
code calls the functions of the ``reviews`` package, which delegate to the
custom app, so custom code can call them too.

.. autofunction:: reviews.get_review_model

   A custom review model should subclass
   :class:`~reviews.models.UserReviewAbstractModel` (see :doc:`models`).

.. autofunction:: reviews.get_review_form

.. autofunction:: reviews.get_review_form_target

.. autofunction:: reviews.get_review_user_weight

   For example, to make ratings of moderators and buyers more valuable:

   .. code-block:: python

        def get_review_user_weight(user, target):
            if user.has_perm('reviews.can_moderate'):
                return 50
            from .models import Product, Order
            if isinstance(target, Product):
                count = Order.objects.filter(user=user.pk,
                                             item__product=target.pk,
                                             status=Order.STATUS_DONE
                                             ).count()
                if count > 0:
                    return 10
            return 1

.. autofunction:: reviews.get_review_site_id

   The default implementation uses ``SITE_ID`` setting and falls back to the
   site of the request. If the site is determined by a custom middleware:

   .. code-block:: python

        def get_review_site_id(request):
            return request.site.id

.. autofunction:: reviews.get_review_rating_text

   The default implementation returns the text from ``REVIEW_RATING_CHOICES``.

.. autofunction:: reviews.get_review_api_user_serializer

   The default :class:`~reviews.api.UserSerializer` exposes only user's
   primary key and its string representation. See :doc:`api`.

.. autofunction:: reviews.get_review_api_pagination_class

   The default is :class:`~reviews.api.ReviewPagination`. See :doc:`api`.
