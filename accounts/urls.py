from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import GoogleConfigView, GoogleLoginView, MeView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register-api"),
    path("google/config/", GoogleConfigView.as_view(), name="google-config"),
    path("google/", GoogleLoginView.as_view(), name="google-auth"),
    path("token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
]
