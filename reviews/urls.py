from django.conf.urls import url
from django.contrib.contenttypes.views import shortcut

from .views import post_review, review_done


urlpatterns = [
    url(r'^post/$', post_review, name='post-review'),
    url(r'^posted/$', review_done, name='review-done'),
    url(r'^rr/(\d+)/(.+)/$', shortcut, name='review-url-redirect'),
]
