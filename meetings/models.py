import uuid

from django.conf import settings
from django.db import models


class Meeting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hosted_meetings",
    )
    subject = models.CharField(max_length=200, blank=True)
    with_whom = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("host", "is_active")),
            models.Index(fields=("scheduled_for", "is_active")),
        ]

    @property
    def is_scheduled(self):
        return self.scheduled_for is not None and self.started_at is None

    def __str__(self):
        return self.subject or str(self.id)


class MeetingAttendance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name="attendance"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meeting_attendance",
    )
    peer_id = models.CharField(max_length=180)
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-joined_at",)
        indexes = [
            models.Index(fields=("user", "joined_at")),
            models.Index(fields=("meeting", "user")),
        ]
