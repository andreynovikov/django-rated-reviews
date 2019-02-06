from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ReviewsAppConfig(AppConfig):
    name = 'reviews'
    verbose_name = _('Reviews')

