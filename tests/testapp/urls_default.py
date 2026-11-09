from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path


urlpatterns = [
    path('', include('reviews.urls')),

    # Provide the auth system login and logout views
    path('accounts/login/', LoginView.as_view(template_name='login.html')),
    path('accounts/logout/', LogoutView.as_view()),
]
