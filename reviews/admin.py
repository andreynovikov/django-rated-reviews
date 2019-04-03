from __future__ import unicode_literals

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ungettext

from . import get_model, DEFAULT_REVIEW_RATING_CHOICES
from .models import Review

REVIEW_RATING_CHOICES = getattr(settings, 'REVIEW_RATING_CHOICES', DEFAULT_REVIEW_RATING_CHOICES)
REVIEW_ADMIN_LINK_SYMBOL = getattr(settings, 'REVIEW_ADMIN_LINK_SYMBOL', '&#9654;')

class UsernameSearch(object):
    """The User object may not be auth.User, so we need to provide
    a mechanism for issuing the equivalent of a .filter(user__username=...)
    search in ReviewAdmin.
    """

    def __str__(self):
        return 'user__%s' % get_user_model().USERNAME_FIELD


class ReviewAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReviewAdminForm, self).__init__(*args, **kwargs)
        self.fields['rating'] = forms.ChoiceField(label=_('Rating'), choices=REVIEW_RATING_CHOICES)

    class Meta:
        model = Review
        fields = '__all__'
        widgets = {
            'object_pk': forms.widgets.TextInput
        }


class ReviewAdmin(admin.ModelAdmin):
    @mark_safe
    def rating_text(self, obj):
        html = "<span style='display: inline-block; vertical-align: text-top; width: {}px; height: 12px; " \
            + "background: url({}reviews/img/star-full.svg)'>&nbsp;</span>&nbsp;{}{}"
        weight = ' &#215; {}'.format(obj.weight) if obj.weight != 1 else ''
        return html.format(obj.rating * 12, settings.STATIC_URL, REVIEW_RATING_CHOICES[obj.rating - 1][1], weight)
    rating_text.short_description = _('rating')
    rating_text.admin_order_field = 'rating'

    @mark_safe
    def link(self, obj):
        if obj.is_public:
            return '<a href="{}">{}</a>'.format(obj.get_absolute_url(), REVIEW_ADMIN_LINK_SYMBOL)
        else:
            return ''
    link.short_description = _('link')

    form = ReviewAdminForm
    fieldsets = (
        (
            None,
            {'fields': ('content_type', 'object_pk', 'site')}
        ),
        (
            _('Content'),
            {'fields': ('user', 'rating', 'weight', 'comment')}
        ),
        (
            _('Metadata'),
            {'fields': ('submit_date', 'ip_address', 'is_public')}
        ),
    )

    list_display = ('user', 'content_type', 'object_pk', 'rating_text', 'ip_address',
                    'submit_date', 'is_public', 'link')
    list_filter = ('submit_date', 'site', 'is_public', 'rating')
    date_hierarchy = 'submit_date'
    raw_id_fields = ('user',)
    search_fields = ('comment', UsernameSearch(), 'ip_address')
    actions = ['approve_reviews']

    def get_actions(self, request):
        actions = super(ReviewAdmin, self).get_actions(request)
        if not request.user.has_perm('reviews.can_moderate'):
            if 'approve_reviews' in actions:
                actions.pop('approve_reviews')
        return actions

    @classmethod
    def perform_approve(cls, review):
        review.is_public = True
        review.save()

    def approve_reviews(self, request, queryset):
        self._bulk_flag(request, queryset, self.perform_approve,
                        lambda n: ungettext('approved', 'approved', n))

    approve_reviews.short_description = _("Approve selected reviews")

    def _bulk_flag(self, request, queryset, action, done_message):
        """
        Flag, approve, or remove some comments from an admin action. Actually
        calls the `action` argument to perform the heavy lifting.
        """
        n_reviews = 0
        for review in queryset:
            action(review)
            n_reviews += 1

        msg = ungettext('%(count)s review was successfully %(action)s.',
                        '%(count)s reviews were successfully %(action)s.',
                        n_reviews)
        self.message_user(request, msg % {'count': n_reviews, 'action': done_message(n_reviews)})


# Only register the default admin if the model is the built-in comment model
# (this won't be true if there's a custom reviews app).
Klass = get_model()
if Klass._meta.app_label == "reviews":
    admin.site.register(Klass, ReviewAdmin)
