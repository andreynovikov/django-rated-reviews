from django.contrib import admin
from django.urls import path

from reviews.admin import ReviewAdmin
from reviews.models import Review

from testapp.models import Article


admin_site = admin.AdminSite()
admin_site.register(Review, ReviewAdmin)
admin_site.register(Article)

urlpatterns = [
    path('admin/', admin_site.urls),
]
