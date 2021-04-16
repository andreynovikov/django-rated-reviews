from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReviewsAppConfig(AppConfig):
    name = 'reviews'
    verbose_name = _('Reviews')
