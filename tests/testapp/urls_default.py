try:
    from django.urls import include, re_path
except ImportError:
    # Django 1.11 - switch to simple path after dropping support of 1.11
    from django.conf.urls import include, url as re_path

from django.contrib.auth.views import LoginView, LogoutView


urlpatterns = [
    re_path(r'^', include('reviews.urls')),

    # Provide the auth system login and logout views
    re_path(r'^accounts/login/$', LoginView.as_view(template_name='login.html')),
    re_path(r'^accounts/logout/$', LogoutView.as_view()),
]
