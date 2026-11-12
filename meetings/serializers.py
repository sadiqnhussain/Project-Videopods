from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Meeting
from .services import build_join_url


class MeetingSerializer(serializers.ModelSerializer):
    meeting_id = serializers.UUIDField(source="id", read_only=True)
    join_url = serializers.SerializerMethodField()
    host_name = serializers.CharField(source="host.name", read_only=True)
    is_host = serializers.SerializerMethodField()
    can_start = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = (
            "meeting_id",
            "join_url",
            "subject",
            "with_whom",
            "created_at",
            "scheduled_for",
            "duration_minutes",
            "started_at",
            "ended_at",
            "is_active",
            "host_name",
            "is_host",
            "can_start",
        )

    def get_join_url(self, obj):
        return build_join_url(obj)

    def get_is_host(self, obj):
        request = self.context.get("request")
        return bool(
            request and request.user.is_authenticated and obj.host_id == request.user.id
        )

    def get_can_start(self, obj):
        request = self.context.get("request")
        if (
            not request
            or not request.user.is_authenticated
            or obj.host_id != request.user.id
        ):
            return False
        if not obj.scheduled_for or obj.is_active:
            return False
        return obj.scheduled_for <= timezone.now() + timedelta(minutes=5)
