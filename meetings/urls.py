from django.urls import path

from .config_api import RTCConfigView
from .views import (
    CreateMeetingView,
    EndMeetingView,
    CancelMeetingView,
    DeleteHistoryView,
    DeleteAllHistoryView,
    MeetingDetailView,
    MeetingHistoryView,
    StartMeetingView,
    UpcomingMeetingsView,
)

urlpatterns = [
    path("rtc-config/", RTCConfigView.as_view(), name="rtc-config"),
    path("create/", CreateMeetingView.as_view(), name="meeting-create"),
    path("history/", MeetingHistoryView.as_view(), name="meeting-history"),
    path(
        "history/<uuid:meeting_id>/",
        DeleteHistoryView.as_view(),
        name="meeting-history-delete",
    ),
    path(
        "history/all/",
        DeleteAllHistoryView.as_view(),
        name="meeting-history-delete-all",
    ),
    path("upcoming/", UpcomingMeetingsView.as_view(), name="meeting-upcoming"),
    path("<uuid:meeting_id>/", MeetingDetailView.as_view(), name="meeting-detail"),
    path("<uuid:meeting_id>/start/", StartMeetingView.as_view(), name="meeting-start"),
    path("<uuid:meeting_id>/end/", EndMeetingView.as_view(), name="meeting-end"),
    path(
        "<uuid:meeting_id>/cancel/", CancelMeetingView.as_view(), name="meeting-cancel"
    ),
]
