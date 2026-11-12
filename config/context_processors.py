from django.conf import settings


def videopods_config(request):
    return {"websocket_meeting_prefix": settings.WEBSOCKET_MEETING_PREFIX}
