from django.contrib import admin
from .models import Meeting


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "host",
        "subject",
        "scheduled_for",
        "duration_minutes",
        "created_at",
        "is_active",
        "ended_at",
    )
    list_filter = ("is_active",)
    search_fields = ("id", "host__email", "host__name")
