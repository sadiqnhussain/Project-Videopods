from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Meeting, MeetingAttendance
from .serializers import MeetingSerializer
from .services import end_meeting, maybe_auto_end_meeting, start_meeting


def meeting_window(meeting):
    if not meeting.scheduled_for or not meeting.duration_minutes:
        return None, None
    start = meeting.scheduled_for
    return start, start + timedelta(minutes=meeting.duration_minutes)


def meeting_state(meeting):
    now = timezone.now()
    start, end = meeting_window(meeting)
    if meeting.ended_at or (end and now >= end and not meeting.is_active):
        return (
            "ended",
            "This meeting has ended. Please contact your host for more information.",
        )
    if start and not meeting.is_active:
        if now < start - timedelta(minutes=5):
            return (
                "too_early",
                f"This meeting will start at {timezone.localtime(start).strftime('%Y-%m-%d %H:%M')}. Please join then.",
            )
        return (
            "waiting",
            f"The meeting will shortly start at {timezone.localtime(start).strftime('%Y-%m-%d %H:%M')}. Please wait patiently.",
        )
    if end and now >= end:
        if meeting.is_active:
            end_meeting(meeting, reason="scheduled_duration_elapsed")
        return (
            "ended",
            "This meeting has ended. Please contact your host for more information.",
        )
    return "active", ""


class CreateMeetingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        subject = str(request.data.get("subject", "")).strip()[:200]
        with_whom = str(request.data.get("with_whom", "")).strip()[:500]
        scheduled_for = request.data.get("scheduled_for")
        duration_minutes = request.data.get("duration_minutes")
        parsed = None
        if scheduled_for:
            try:
                parsed = datetime.fromisoformat(
                    str(scheduled_for).replace("Z", "+00:00")
                )
                if timezone.is_naive(parsed):
                    parsed = timezone.make_aware(
                        parsed, timezone.get_current_timezone()
                    )
                if parsed <= timezone.now():
                    return Response(
                        {"scheduled_for": "Choose a future date and time."}, status=400
                    )
            except ValueError:
                return Response(
                    {"scheduled_for": "Use a valid date and time."}, status=400
                )
            try:
                duration_minutes = int(duration_minutes)
            except (TypeError, ValueError):
                return Response(
                    {"duration_minutes": "Choose a meeting duration."}, status=400
                )
            if duration_minutes < 5 or duration_minutes > 720:
                return Response(
                    {
                        "duration_minutes": "Duration must be between 5 minutes and 12 hours."
                    },
                    status=400,
                )
        else:
            duration_minutes = None

        meeting = Meeting.objects.create(
            host=request.user,
            subject=subject,
            with_whom=with_whom,
            scheduled_for=parsed,
            duration_minutes=duration_minutes,
            started_at=None if parsed else timezone.now(),
            is_active=not bool(parsed),
        )
        return Response(
            MeetingSerializer(meeting, context={"request": request}).data, status=201
        )


class MeetingDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = get_object_or_404(
            Meeting.objects.select_related("host"), pk=meeting_id
        )
        if meeting.is_active:
            maybe_auto_end_meeting(meeting)
            meeting.refresh_from_db()
        state, message = meeting_state(meeting)
        data = MeetingSerializer(meeting, context={"request": request}).data
        data.update(
            {
                "access_state": state,
                "access_message": message,
                "can_join": state == "active",
            }
        )
        return Response(data)


class EndMeetingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, pk=meeting_id)
        if meeting.host_id != request.user.id:
            return Response(
                {"detail": "Only the host can end this meeting."}, status=403
            )
        end_meeting(meeting, reason="host_ended")
        return Response(MeetingSerializer(meeting, context={"request": request}).data)


class StartMeetingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, pk=meeting_id)
        if meeting.host_id != request.user.id:
            return Response(
                {"detail": "Only the host can start this meeting."}, status=403
            )
        if meeting.is_active:
            return Response(
                MeetingSerializer(meeting, context={"request": request}).data
            )
        if not meeting.scheduled_for:
            return Response({"detail": "This meeting is not scheduled."}, status=400)
        start, end = meeting_window(meeting)
        if timezone.now() < start - timedelta(minutes=5):
            return Response(
                {
                    "detail": "You can start this meeting from five minutes before its scheduled time."
                },
                status=400,
            )
        if end and timezone.now() >= end:
            return Response(
                {"detail": "This scheduled meeting has expired."}, status=400
            )
        start_meeting(meeting)
        return Response(MeetingSerializer(meeting, context={"request": request}).data)


class CancelMeetingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, pk=meeting_id)
        if meeting.host_id != request.user.id:
            return Response(
                {"detail": "Only the host can cancel this meeting."}, status=403
            )
        if meeting.is_active:
            return Response(
                {"detail": "An active meeting cannot be cancelled."}, status=400
            )
        meeting.is_active = False
        meeting.ended_at = timezone.now()
        meeting.save(update_fields=["is_active", "ended_at"])
        return Response({"detail": "Meeting cancelled."})


class MeetingHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rows = []
        meetings = (
            Meeting.objects.select_related("host")
            .filter(attendance__user=request.user)
            .distinct()
            .order_by("-created_at")[:100]
        )
        for meeting in meetings:
            sessions = meeting.attendance.filter(user=request.user)
            seconds = 0
            for session in sessions:
                end = session.left_at or (meeting.ended_at or timezone.now())
                seconds += max(0, int((end - session.joined_at).total_seconds()))
            rows.append(
                {
                    "meeting_id": str(meeting.id),
                    "subject": meeting.subject or "Untitled meeting",
                    "date": timezone.localtime(
                        meeting.started_at or meeting.created_at
                    ).strftime("%Y-%m-%d"),
                    "time": timezone.localtime(
                        meeting.started_at or meeting.created_at
                    ).strftime("%H:%M"),
                    "duration_seconds": seconds,
                    "hosted_by": meeting.host.name
                    or meeting.host.username
                    or meeting.host.email,
                }
            )
        return Response(rows)


class DeleteHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, meeting_id):
        MeetingAttendance.objects.filter(
            meeting_id=meeting_id, user=request.user
        ).delete()
        return Response(status=204)


class DeleteAllHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        MeetingAttendance.objects.filter(user=request.user).delete()
        return Response(status=204)


class UpcomingMeetingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        meetings = Meeting.objects.filter(
            host=request.user,
            is_active=False,
            scheduled_for__isnull=False,
            ended_at__isnull=True,
        ).order_by("scheduled_for")[:100]
        return Response(
            MeetingSerializer(meetings, many=True, context={"request": request}).data
        )
