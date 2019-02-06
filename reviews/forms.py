import time

from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.forms.utils import ErrorDict
from django.utils.crypto import salted_hmac, constant_time_compare
from django.utils.encoding import force_text
from django.utils.text import get_text_list
from django.utils import timezone
from django.utils.translation import ungettext, ugettext, ugettext_lazy as _

from . import get_model, DEFAULT_REVIEW_RATING_CHOICES


REVIEW_MAX_LENGTH = getattr(settings, 'REVIEW_MAX_LENGTH', 3000)
REVIEW_PUBLISH_UNMODERATED = getattr(settings, 'REVIEW_PUBLISH_UNMODERATED', False)
DEFAULT_REVIEW_TIMEOUT = getattr(settings, 'REVIEW_COMPOSE_TIMEOUT', (2 * 60 * 60))  # 2h
REVIEW_RATING_CHOICES = getattr(settings, 'REVIEW_RATING_CHOICES', DEFAULT_REVIEW_RATING_CHOICES)

class ReviewSecurityForm(forms.Form):
    """
    Handles the security aspects (anti-spoofing) for review forms.
    """
    id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    content_type = forms.CharField(widget=forms.HiddenInput)
    object_pk = forms.CharField(widget=forms.HiddenInput)
    timestamp = forms.IntegerField(widget=forms.HiddenInput)
    security_hash = forms.CharField(min_length=40, max_length=40, widget=forms.HiddenInput)

    def __init__(self, target_object, data=None, initial=None, **kwargs):
        self.target_object = target_object
        if initial is None:
            initial = {}
        initial.update(self.generate_security_data())
        super(ReviewSecurityForm, self).__init__(data=data, initial=initial, **kwargs)

    def security_errors(self):
        """Return just those errors associated with security"""
        errors = ErrorDict()
        for f in ["honeypot", "timestamp", "security_hash"]:
            if f in self.errors:
                errors[f] = self.errors[f]
        return errors

    def clean_security_hash(self):
        """Check the security hash."""
        security_hash_dict = {
            'content_type': self.data.get("content_type", ""),
            'object_pk': self.data.get("object_pk", ""),
            'timestamp': self.data.get("timestamp", ""),
        }
        expected_hash = self.generate_security_hash(**security_hash_dict)
        actual_hash = self.cleaned_data["security_hash"]
        if not constant_time_compare(expected_hash, actual_hash):
            raise forms.ValidationError("Security hash check failed.")
        return actual_hash

    def clean_timestamp(self):
        """Make sure the timestamp isn't too far (default is 2 hours) in the past."""
        ts = self.cleaned_data["timestamp"]
        if time.time() - ts > DEFAULT_REVIEW_TIMEOUT:
            raise forms.ValidationError("Timestamp check failed")
        return ts

    def generate_security_data(self):
        """Generate a dict of security data for "initial" data."""
        timestamp = int(time.time())
        security_dict = {
            'content_type': str(self.target_object._meta),
            'object_pk': str(self.target_object._get_pk_val()),
            'timestamp': str(timestamp),
            'security_hash': self.initial_security_hash(timestamp),
        }
        return security_dict

    def initial_security_hash(self, timestamp):
        """
        Generate the initial security hash from self.content_object
        and a (unix) timestamp.
        """
        initial_security_dict = {
            'content_type': str(self.target_object._meta),
            'object_pk': str(self.target_object._get_pk_val()),
            'timestamp': str(timestamp),
        }
        return self.generate_security_hash(**initial_security_dict)

    def generate_security_hash(self, content_type, object_pk, timestamp):
        """
        Generate a HMAC security hash from the provided info.
        """
        info = (content_type, object_pk, timestamp)
        key_salt = "django.contrib.forms.CommentSecurityForm"
        value = "-".join(info)
        return salted_hmac(key_salt, value).hexdigest()


class ReviewDetailsForm(ReviewSecurityForm):
    """
    Handles the specific details of the review.
    """
    rating_choices = (("", _("Select a rating")),) + REVIEW_RATING_CHOICES
    rating = forms.IntegerField(label=_('Rating'),
                                widget=forms.Select(choices=rating_choices, attrs={'class':'star-rating'}),
                                required=True)
    # Translators: 'Comment' is a noun here.
    comment = forms.CharField(label=_('Comment'),
                              widget=forms.Textarea(),
                              max_length=REVIEW_MAX_LENGTH,
                              required=True)

    class Media:
        minified = '' if settings.DEBUG else '.min'
        css = {
            'all': ('reviews/css/star-rating{}.css'.format(minified),)
            }
        js = ('reviews/js/star-rating{}.js'.format(minified),)

    def update_review_object(self, review):
        """
        Update existing review object with new information in this form.
        Assumes that the form is already validated and will throw a ValueError if not.
        """
        if not self.is_valid():
            raise ValueError("update_review_object may only be called on valid forms")

        if review.content_type != ContentType.objects.get_for_model(self.target_object):
            raise ValueError("Object content type spoofed")
        if review.object_pk != force_text(self.target_object._get_pk_val()):
            raise ValueError("Object pk spoofed")
        review.rating = self.cleaned_data["rating"]
        review.comment = self.cleaned_data["comment"]
        review.submit_date = timezone.now()
        review.is_public=REVIEW_PUBLISH_UNMODERATED

    def get_review_object(self, site_id=None):
        """
        Return a new (unsaved) review object based on the information in this
        form. Assumes that the form is already validated and will throw a
        ValueError if not.

        Does not set any of the fields that would come from a Request object
        (i.e. ``user`` or ``ip_address``).
        """
        if not self.is_valid():
            raise ValueError("get_review_object may only be called on valid forms")

        ReviewModel = self.get_review_model()
        return ReviewModel(**self.get_review_create_data(site_id=site_id))

    def get_review_model(self):
        """
        Get the review model to create with this form. Subclasses in custom
        reviews apps should override this, get_review_create_data to provide
        custom review models.
        """
        return get_model()

    def get_review_create_data(self, site_id=None):
        """
        Returns the dict of data to be used to create a review.
        """
        return dict(
            content_type=ContentType.objects.get_for_model(self.target_object),
            object_pk=force_text(self.target_object._get_pk_val()),
            rating=self.cleaned_data["rating"],
            comment=self.cleaned_data["comment"],
            submit_date=timezone.now(),
            site_id=site_id or getattr(settings, "SITE_ID", None),
            is_public=REVIEW_PUBLISH_UNMODERATED
        )

    def clean_rating(self):
        """
        Rating should be set (by javascript) and contain a valid number.
        """
        rating = self.cleaned_data["rating"]
        if rating < 1 or rating > len(REVIEW_RATING_CHOICES):
            raise forms.ValidationError(_("Rating should be between %(min)d and %(max)d") % {'min': 1, 'max': len(REVIEW_RATING_CHOICES)})
        return rating

    def clean_comment(self):
        """
        If REVIEW_ALLOW_PROFANITIES is False, check that the comment doesn't
        contain anything in PROFANITIES_LIST.
        """
        comment = self.cleaned_data["comment"]
        if (not getattr(settings, 'REVIEW_ALLOW_PROFANITIES', False) and
                getattr(settings, 'PROFANITIES_LIST', False)):
            bad_words = [w for w in settings.PROFANITIES_LIST if w in comment.lower()]
            if bad_words:
                raise forms.ValidationError(ungettext(
                    "Watch your mouth! The word %s is not allowed here.",
                    "Watch your mouth! The words %s are not allowed here.",
                    len(bad_words)) % get_text_list(
                    ['"%s%s%s"' % (i[0], '-' * (len(i) - 2), i[-1])
                     for i in bad_words], ugettext('and')))
        return comment


class ReviewForm(ReviewDetailsForm):
    honeypot = forms.CharField(required=False, label='',
                               widget=forms.TextInput(attrs={'style':'display:none'}))

    def clean_honeypot(self):
        """Check that nothing's been entered into the honeypot."""
        value = self.cleaned_data["honeypot"]
        if value:
            raise forms.ValidationError(self.fields["honeypot"].label)
        return value
