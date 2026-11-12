from django.http import Http404
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.urls import path

from .models import Meeting
from .views import meeting_state


class DashboardPageView(TemplateView):
    template_name = "dashboard.html"


def not_found_view(request, exception=None, meeting_id=None):
    return render(request, "404.html", {"meeting_id": meeting_id}, status=404)


class MeetingPageView(View):

    def get(self, request, meeting_id):
        try:
            meeting = Meeting.objects.select_related("host").get(pk=meeting_id)
        except Meeting.DoesNotExist:
            return not_found_view(request)
        state, message = meeting_state(meeting)
        return render(
            request,
            "meeting.html",
            {
                "meeting_id": str(meeting.id),
                "meeting_subject": meeting.subject or "Videopods meeting",
                "meeting_access_state": state,
                "meeting_access_message": message,
                "meeting_scheduled_for": meeting.scheduled_for,
            },
        )


urlpatterns = [
    path("404/", not_found_view, name="not-found"),
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
    path("login/", TemplateView.as_view(template_name="login.html"), name="login"),
    path(
        "register/",
        TemplateView.as_view(template_name="register.html"),
        name="register",
    ),
    path("dashboard/", DashboardPageView.as_view(), name="dashboard"),
    path(
        "meeting/ended/review-or-skip/",
        TemplateView.as_view(template_name="ended.html"),
        name="meeting-ended",
    ),
    path("meeting/<uuid:meeting_id>/", MeetingPageView.as_view(), name="meeting"),
    path("meeting/<path:meeting_id>/", not_found_view, name="invalid-meeting"),
]
