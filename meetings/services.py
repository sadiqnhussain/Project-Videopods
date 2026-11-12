from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.utils import timezone

from .models import Meeting


def build_join_url(meeting):
    return f"{settings.PUBLIC_BASE_URL}/meeting/{meeting.id}/"


def start_meeting(meeting):
    Meeting.objects.filter(pk=meeting.pk, is_active=False).update(
        is_active=True, started_at=timezone.now()
    )
    meeting.refresh_from_db()
    return meeting


def end_meeting(meeting, reason="host_ended"):
    updated = Meeting.objects.filter(pk=meeting.pk, is_active=True).update(
        is_active=False, ended_at=timezone.now()
    )
    if updated:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"meeting_{meeting.id}",
            {"type": "meeting.ended", "reason": reason},
        )
    meeting.refresh_from_db()
    return meeting


def maybe_auto_end_meeting(meeting):
    """End an active meeting when the host has been absent for three minutes."""
    if not meeting.is_active or not meeting.host_id:
        return meeting
    host_session = (
        meeting.attendance.filter(user_id=meeting.host_id)
        .order_by("-joined_at")
        .first()
    )
    if (
        host_session
        and host_session.left_at
        and host_session.left_at <= timezone.now() - timedelta(minutes=3)
    ):
        return end_meeting(meeting, reason="host_absent")
    return meeting


def expire_scheduled_meeting_if_needed(meeting):
    if meeting.is_active and meeting.scheduled_for and meeting.duration_minutes:
        if timezone.now() >= meeting.scheduled_for + timedelta(
            minutes=meeting.duration_minutes
        ):
            return end_meeting(meeting, reason="scheduled_duration_elapsed")
    return meeting
