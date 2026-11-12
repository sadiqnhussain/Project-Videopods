from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Meeting

User = get_user_model()


class MeetingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            name="Alice",
            password="pass123",
        )
        self.client.force_authenticate(self.user)

    def test_create_and_end_meeting(self):
        response = self.client.post("/api/meetings/create/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        meeting_id = response.data["meeting_id"]
        self.assertTrue(response.data["join_url"].endswith(f"/meeting/{meeting_id}/"))

        end = self.client.post(f"/api/meetings/{meeting_id}/end/", {}, format="json")
        self.assertEqual(end.status_code, 200)
        self.assertFalse(Meeting.objects.get(pk=meeting_id).is_active)

    def test_non_host_cannot_end(self):
        meeting = Meeting.objects.create(host=self.user)
        other = User.objects.create_user(
            username="bob", email="bob@example.com", name="Bob", password="pass123"
        )
        self.client.force_authenticate(other)
        response = self.client.post(
            f"/api/meetings/{meeting.id}/end/", {}, format="json"
        )
        self.assertEqual(response.status_code, 403)


class ScheduledMeetingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="host", email="host@example.com", name="Host", password="pass123"
        )
        self.client.force_authenticate(self.user)

    def test_schedule_and_start_within_five_minutes(self):
        from django.utils import timezone
        from datetime import timedelta

        scheduled = timezone.now() + timedelta(minutes=4)
        response = self.client.post(
            "/api/meetings/create/",
            {
                "subject": "Demo",
                "with_whom": "Team",
                "scheduled_for": scheduled.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["is_active"])
        meeting_id = response.data["meeting_id"]
        start = self.client.post(
            f"/api/meetings/{meeting_id}/start/", {}, format="json"
        )
        self.assertEqual(start.status_code, 200)
        self.assertTrue(start.data["is_active"])
