from django.conf.urls import re_path
from django.contrib.contenttypes.views import shortcut

from .views import post_review, review_done


urlpatterns = [
    re_path(r'^post/$', post_review, name='post-review'),
    re_path(r'^posted/$', review_done, name='review-done'),
    re_path(r'^rr/(\d+)/(.+)/$', shortcut, name='review-url-redirect'),
]
