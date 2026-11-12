from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class RTCConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        servers = []
        if settings.STUN_URL:
            servers.append({"urls": settings.STUN_URL})
        if settings.TURN_URL:
            servers.append(
                {
                    "urls": settings.TURN_URL,
                    "username": settings.TURN_USERNAME,
                    "credential": settings.TURN_PASSWORD,
                }
            )
        return Response(
            {"ice_servers": servers, "google_client_id": settings.GOOGLE_CLIENT_ID}
        )
