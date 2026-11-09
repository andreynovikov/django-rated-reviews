from django.contrib.contenttypes.views import shortcut
from django.urls import path

from .views import post_review, review_done


urlpatterns = [
    path('post/', post_review, name='post-review'),
    path('posted/', review_done, name='review-done'),
    path('rr/<int:content_type_id>/<path:object_id>/', shortcut, name='review-url-redirect'),
]
