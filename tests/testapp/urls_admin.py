try:
    from django.urls import re_path
except ImportError:
    # Django 1.11 - switch to simple path after dropping support of 1.11
    from django.conf.urls import url as re_path

from django.contrib import admin
from reviews.admin import ReviewAdmin
from reviews.models import Review

from testapp.models import Article


admin_site = admin.AdminSite()
admin_site.register(Review, ReviewAdmin)
admin_site.register(Article)

urlpatterns = [
    re_path(r'^admin/', admin_site.urls),
]
