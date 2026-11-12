from datetime import datetime, timedelta
import asyncio
from urllib.parse import parse_qs
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Meeting, MeetingAttendance
from .services import expire_scheduled_meeting_if_needed, maybe_auto_end_meeting

User = get_user_model()


class MeetingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.meeting_id = self.scope["url_route"]["kwargs"]["meeting_id"]
        self.group_name = f"meeting_{self.meeting_id}"
        self.user = await self._authenticate()
        if self.user is None:
            await self.close(code=4401)
            return
        self.meeting = await self._get_meeting()
        if self.meeting is None:
            await self.close(code=4404)
            return
        if self.meeting.is_active:
            self.meeting = await self._expire_if_needed(self.meeting)
            self.meeting = await self._maybe_auto_end(self.meeting)
        if not self.meeting.is_active:
            await self.close(code=4409)
            return

        self.peer_id = f"{self.user.id}:{self.channel_name[-8:]}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._start_attendance()
        await self.send_json(
            {
                "type": "connected",
                "peer_id": self.peer_id,
                "is_host": self.meeting.host_id == self.user.id,
                "name": self.user.name or self.user.username or self.user.email,
                "subject": self.meeting.subject,
            }
        )
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "participant.joined",
                "peer_id": self.peer_id,
                "user_id": self.user.id,
                "name": self.user.name or self.user.username or self.user.email,
                "is_host": self.meeting.host_id == self.user.id,
            },
        )
        await self.receive_json({"type": "roster_request"})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, "peer_id"):
            was_host = bool(
                getattr(self, "meeting", None) and self.meeting.host_id == self.user.id
            )
            await self._finish_attendance()
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "participant.left", "peer_id": self.peer_id},
            )
            if was_host:
                asyncio.create_task(self._auto_end_after_host_grace())

    async def receive_json(self, content, **kwargs):
        message_type = content.get("type")
        if message_type in {"offer", "answer", "ice_candidate", "media_state"}:
            target = content.get("target")
            if not target:
                return
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "signal.forward",
                    "sender": self.peer_id,
                    "target": target,
                    "payload": content,
                },
            )
            return

        if message_type == "roster_request":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "roster.request",
                    "requester": self.peer_id,
                    "requester_name": self.user.name
                    or self.user.username
                    or self.user.email,
                    "sender": self.peer_id,
                },
            )
            return

        if message_type == "peer_announce":
            target = content.get("target")
            if target:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "peer.announce",
                        "target": target,
                        "peer_id": self.peer_id,
                        "name": self.user.name or self.user.username or self.user.email,
                        "is_host": self.meeting.host_id == self.user.id,
                    },
                )

    async def participant_joined(self, event):
        if event["peer_id"] == getattr(self, "peer_id", None):
            return
        await self.send_json(
            {
                "type": "participant_joined",
                "peer_id": event["peer_id"],
                "user_id": event["user_id"],
                "name": event["name"],
                "is_host": event.get("is_host", False),
            }
        )

    async def participant_left(self, event):
        if event["peer_id"] != getattr(self, "peer_id", None):
            await self.send_json(
                {"type": "participant_left", "peer_id": event["peer_id"]}
            )

    async def roster_request(self, event):
        if event.get("sender") == self.peer_id:
            return
        await self.send_json(
            {
                "type": "roster_request",
                "target": event["requester"],
                "requester": event["requester"],
                "requester_name": event.get("requester_name", "Participant"),
            }
        )

    async def peer_announce(self, event):
        if event["target"] == self.peer_id and event["peer_id"] != self.peer_id:
            await self.send_json(
                {
                    "type": "peer_announce",
                    "peer_id": event["peer_id"],
                    "name": event["name"],
                    "is_host": event.get("is_host", False),
                }
            )

    async def signal_forward(self, event):
        if event["target"] == self.peer_id or (
            event["target"] == "*" and event["sender"] != self.peer_id
        ):
            payload = dict(event["payload"])
            payload["sender"] = event["sender"]
            await self.send_json(payload)

    async def meeting_ended(self, event):
        await self.send_json(
            {"type": "MEETING_ENDED", "reason": event.get("reason", "host_ended")}
        )
        await self.close(code=4000)

    async def _auto_end_after_host_grace(self):
        await asyncio.sleep(180)
        meeting = await self._get_meeting()
        if meeting is None or not meeting.is_active:
            return
        await self._maybe_auto_end(meeting)

    @database_sync_to_async
    def _expire_if_needed(self, meeting):
        return expire_scheduled_meeting_if_needed(meeting)

    @database_sync_to_async
    def _maybe_auto_end(self, meeting):
        return maybe_auto_end_meeting(meeting)

    async def _authenticate(self):
        token = self._get_token()
        if not token:
            return None
        try:
            validated = JWTAuthentication().get_validated_token(token)
            user_id = validated.get("user_id")
            return await User.objects.aget(pk=user_id, is_active=True)
        except Exception:
            return None

    def _get_token(self):
        query = parse_qs(self.scope.get("query_string", b"").decode("utf-8"))
        token = query.get("token", [None])[0]
        if token:
            return token
        for name, value in self.scope.get("headers", []):
            if name.lower() == b"authorization" and value.lower().startswith(
                b"bearer "
            ):
                return value[7:].decode("utf-8")
        return None

    async def _get_meeting(self):
        try:
            UUID(str(self.meeting_id))
        except ValueError:
            return None
        return (
            await Meeting.objects.select_related("host")
            .filter(pk=self.meeting_id)
            .afirst()
        )

    @database_sync_to_async
    def _start_attendance(self):
        MeetingAttendance.objects.create(
            meeting_id=self.meeting_id,
            user_id=self.user.id,
            peer_id=self.peer_id,
            joined_at=timezone.now(),
        )

    @database_sync_to_async
    def _finish_attendance(self):
        session = (
            MeetingAttendance.objects.filter(
                meeting_id=self.meeting_id, peer_id=self.peer_id, left_at__isnull=True
            )
            .order_by("-joined_at")
            .first()
        )
        if session:
            session.left_at = timezone.now()
            session.save(update_fields=["left_at"])
