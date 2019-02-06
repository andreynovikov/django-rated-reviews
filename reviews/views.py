from __future__ import absolute_import

try:
    from urllib.parse import urlencode
except ImportError:
    # Python 2
    from urllib import urlencode

from django import http
from django.apps import apps
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import render, resolve_url
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.http import is_safe_url
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from . import signals, get_model, get_form, get_user_weight


SHOW_RATING_TEXT = getattr(settings, 'REVIEW_SHOW_RATING_TEXT', True)


class ReviewPostBadRequest(http.HttpResponseBadRequest):
    """
    Response returned when a review post is invalid. If ``DEBUG`` is on a
    nice-ish error message will be displayed (for debugging purposes), but in
    production mode a simple opaque 400 page will be displayed.
    """

    def __init__(self, why):
        super(ReviewPostBadRequest, self).__init__()
        if settings.DEBUG:
            self.content = render_to_string("reviews/400-debug.html", {"why": why})


@csrf_protect
@require_POST
def post_review(request, next=None, using=None):
    """
    Post a review.

    HTTP POST is required.
    """
    data = request.POST.copy()

    # Look up the object we're trying to comment about
    ctype = data.get("content_type")
    object_pk = data.get("object_pk")
    if ctype is None or object_pk is None:
        return ReviewPostBadRequest("Missing content_type or object_pk field.")
    try:
        model = apps.get_model(*ctype.split(".", 1))
        target = model._default_manager.using(using).get(pk=object_pk)
    except TypeError:
        return ReviewPostBadRequest("Invalid content_type value: %r" % escape(ctype))
    except AttributeError:
        return ReviewPostBadRequest("The given content-type %r does not resolve to a valid model." % escape(ctype))
    except ObjectDoesNotExist:
        return ReviewPostBadRequest("No object matching content-type %r and object PK %r exists." % (escape(ctype), escape(object_pk)))
    except (ValueError, ValidationError) as e:
        return ReviewPostBadRequest("Attempting to get content-type %r and object PK %r exists raised %s" % (escape(ctype), escape(object_pk), e.__class__.__name__))

    # Construct the review form
    form = get_form()(target, data=data)

    # Check security information
    if form.security_errors():
        return ReviewPostBadRequest("The comment form failed security verification: %s" % escape(str(form.security_errors())))

    # If there are errors show the review
    if form.errors:
        template_list = [
            "reviews/%s/%s/post.html" % (model._meta.app_label, model._meta.model_name),
            "reviews/%s/post.html" % model._meta.app_label,
            "reviews/post.html",
        ]
        return render(request, template_list, {
                "target": target,
                "comment": form.data.get("comment", ""),
                "rating": form.data.get("rating", ""),
                "form": form,
                "next": data.get("next", next),
                "show_rating_text": SHOW_RATING_TEXT,
            },
        )

    # Get existing review
    if form.cleaned_data["id"] is not None:
        try:
            review = form.get_review_model().objects.get(pk=form.cleaned_data["id"])
        except model.DoesNotExist:
            return ReviewPostBadRequest("Referenced object gone")
        if review.user != request.user:
            return ReviewPostBadRequest("User spoofing")
        form.update_review_object(review)
    else:
        # Otherwise create the review
        review = form.get_review_object(site_id=get_current_site(request).id)
        if request.user.is_authenticated:
            review.user = request.user

    review.weight = get_user_weight(request.user, target)
    review.ip_address = request.META.get("REMOTE_ADDR", None) or None

    # Save the review and signal that it was saved
    review.save()
    signals.review_was_posted.send(sender=review.__class__, review=review, request=request)

    return next_redirect(request, fallback=next or 'review-done', r=review._get_pk_val())


def next_redirect(request, fallback, **get_kwargs):
    """
    Handle the "where should I go next?" part of comment views.

    The next value could be a ``?next=...`` GET arg or the URL of a given view (``fallback``). See
    the view modules for examples.

    Returns an ``HttpResponseRedirect``.
    """
    next = request.POST.get('next')
    if not is_safe_url(url=next, allowed_hosts={request.get_host()}):
        next = resolve_url(fallback)

    if get_kwargs:
        if '#' in next:
            tmp = next.rsplit('#', 1)
            next = tmp[0]
            anchor = '#' + tmp[1]
        else:
            anchor = ''

        joiner = ('?' in next) and '&' or '?'
        next += joiner + urlencode(get_kwargs) + anchor
    return http.HttpResponseRedirect(next)


def review_done(request):
    review = None
    template="reviews/posted.html"
    if 'r' in request.GET:
        try:
            review = get_model().objects.get(pk=request.GET['r'])
        except (ObjectDoesNotExist, ValueError):
            pass
    return render(request, template, {'review': review})
