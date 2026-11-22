=======
Signals
=======

.. data:: reviews.signals.review_was_posted

   Sent just after a review is saved by the review form view or the REST API,
   both when a review is posted and when it is modified. Arguments:

   ``sender``
       The review model.

   ``review``
       The saved review.

   ``request``
       The request that posted the review.

Notifying about new reviews
===========================

The application doesn't send mail itself, but a receiver of
``review_was_posted`` can. For example, to tell the site managers (the
``MANAGERS`` setting) about every review that waits for moderation:

.. code-block:: python

    # myapp/receivers.py
    from django.core.mail import mail_managers
    from django.dispatch import receiver
    from django.urls import reverse

    from reviews.signals import review_was_posted


    @receiver(review_was_posted)
    def notify_managers(sender, review, request, **kwargs):
        if review.is_public:
            return
        url = request.build_absolute_uri(reverse('admin:reviews_review_change', args=[review.pk]))
        mail_managers(
            f'New review of {review.content_object}',
            f'{review.user or "Anonymous"} rated it {review.rating}:\n\n{review.comment}\n\n{url}',
        )

Import the receivers when your application is ready:

.. code-block:: python

    # myapp/apps.py
    from django.apps import AppConfig


    class MyAppConfig(AppConfig):
        name = 'myapp'

        def ready(self):
            from . import receivers  # noqa: F401

The admin URL name above is for the default review model, a custom review
model has its own. Mail is sent while the request is handled, so posting a
review waits for the mail server. If that is slow, send the mail from a task
queue such as Celery.
