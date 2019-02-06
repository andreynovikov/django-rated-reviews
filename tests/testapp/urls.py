from __future__ import absolute_import

from django.conf.urls import url
from django.contrib.contenttypes.views import shortcut

from custom_reviews import views


urlpatterns = [
    url(r'^post/$', views.custom_submit_review),
    url(r'^rr/(\d+)/(.+)/$', shortcut, name='review-url-redirect'),
]
