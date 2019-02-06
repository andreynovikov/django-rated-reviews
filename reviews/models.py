from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .managers import ReviewManager


REVIEW_MAX_LENGTH = getattr(settings, 'REVIEW_MAX_LENGTH', 3000)
REVIEW_PUBLISH_UNMODERATED = getattr(settings, 'REVIEW_PUBLISH_UNMODERATED', False)


class BaseReviewAbstractModel(models.Model):
    """
    An abstract base class that any custom review models should subclass.
    """
    content_type = models.ForeignKey(ContentType,
                                     verbose_name=_('content type'),
                                     related_name="content_type_set_for_%(class)s",
                                     on_delete=models.CASCADE)
    object_pk = models.TextField(_('object ID'))
    content_object = GenericForeignKey(ct_field="content_type", fk_field="object_pk")

    comment = models.TextField(_('comment'), max_length=REVIEW_MAX_LENGTH)
    rating = models.PositiveSmallIntegerField(_('rating'))
    weight = models.PositiveSmallIntegerField(_('weight'), default=1)

    class Meta:
        abstract = True

    def get_content_object_url(self):
        """
        Get a URL suitable for redirecting to the content object.
        """
        return reverse("review-url-redirect", args=(self.content_type_id, self.object_pk))


class Review(BaseReviewAbstractModel):
    """
    A user review for some object.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                             blank=True, null=True, related_name="%(class)s_comments",
                             on_delete=models.SET_NULL)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    submit_date = models.DateTimeField(_('submitted at'), default=None, db_index=True)
    ip_address = models.GenericIPAddressField(_('IP address'), unpack_ipv4=True, blank=True, null=True)
    is_public = models.BooleanField(_('is public'), default=REVIEW_PUBLISH_UNMODERATED,
                                    help_text=_('Check this box to publish review on the site.'))

    objects = ReviewManager()

    class Meta:
        ordering = ('-submit_date',)
        permissions = [("can_moderate", "Can moderate reviews")]
        verbose_name = _('review')
        verbose_name_plural = _('reviews')

    def get_absolute_url(self, anchor_pattern="#r%(id)s"):
        return self.get_content_object_url() + (anchor_pattern % self.__dict__)

    def __str__(self):
        return _("%(user)s review of %(object)s") % {'user': self.user, 'object': self.content_object}

    def save(self, *args, **kwargs):
        if self.submit_date is None:
            self.submit_date = timezone.now()
        super(Review, self).save(*args, **kwargs)
