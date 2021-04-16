try:
    from django.urls import re_path
except ImportError:
    # Django 1.11 - switch to simple path after dropping support of 1.11
    from django.conf.urls import url as re_path

from django.contrib.contenttypes.views import shortcut

from custom_reviews import views


urlpatterns = [
    re_path(r'^post/$', views.custom_submit_review),
    re_path(r'^rr/(\d+)/(.+)/$', shortcut, name='review-url-redirect'),
]
