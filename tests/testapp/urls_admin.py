from django.conf.urls import url
from django.contrib import admin
from reviews.admin import ReviewAdmin
from reviews.models import Review

from testapp.models import Article


admin_site = admin.AdminSite()
admin_site.register(Review, ReviewAdmin)
admin_site.register(Article)

urlpatterns = [
    url(r'^admin/', admin_site.urls),
]
