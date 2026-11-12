from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import RegisterSerializer, UserSerializer, token_pair

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(token_pair(user), status=status.HTTP_201_CREATED)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class GoogleConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"google_client_id": settings.GOOGLE_CLIENT_ID})


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        google_token = request.data.get("id_token")
        if not google_token:
            return Response(
                {"detail": "id_token is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not settings.GOOGLE_CLIENT_ID:
            return Response(
                {"detail": "Google sign-in is not configured on this server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            payload = id_token.verify_oauth2_token(
                google_token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except Exception:
            return Response(
                {"detail": "The Google credential could not be verified."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = str(payload.get("email", "")).lower().strip()
        if not email or payload.get("email_verified") is not True:
            return Response(
                {"detail": "A verified Google email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            local = (
                "".join(ch for ch in email.split("@", 1)[0] if ch.isalnum())[:100]
                or "google"
            )
            username = local
            while User.objects.filter(username=username).exists():
                username = f"{local}-{get_random_string(5).lower()}"
            user = User.objects.create_user(
                username=username,
                email=email,
                name=(payload.get("name") or email.split("@", 1)[0])[:255],
                password=None,
            )
            user.is_google_account = True
            user.save(update_fields=["is_google_account"])
        elif not user.is_google_account:
            user.is_google_account = True
            user.save(update_fields=["is_google_account"])

        return Response(token_pair(user))
