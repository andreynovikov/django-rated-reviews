from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReviewsAppConfig(AppConfig):
    name = 'reviews'
    verbose_name = _('Reviews')
    # Pinned so that migrations do not depend on project's DEFAULT_AUTO_FIELD
    default_auto_field = 'django.db.models.BigAutoField'
