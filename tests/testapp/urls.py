from django.contrib.contenttypes.views import shortcut
from django.urls import path

from custom_reviews import views


urlpatterns = [
    path('post/', views.custom_submit_review),
    path('rr/<int:content_type_id>/<path:object_id>/', shortcut, name='review-url-redirect'),
]
