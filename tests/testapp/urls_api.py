from django.urls import include, path

from rest_framework.routers import DefaultRouter

from reviews.api import ReviewViewSet


router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'reviews/(?P<model>\w+\.\w+)/(?P<identifier>[^/.]+)', ReviewViewSet, basename='model-review')

urlpatterns = [
    path('', include('reviews.urls')),
    path('api/', include(router.urls)),
]
