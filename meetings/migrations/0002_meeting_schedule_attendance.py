from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("meetings", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="meeting",
            name="subject",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="meeting",
            name="with_whom",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="meeting",
            name="scheduled_for",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="meeting",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="meeting",
            index=models.Index(
                fields=["scheduled_for", "is_active"],
                name="meetings_me_schedu_4f2b0c_idx",
            ),
        ),
        migrations.CreateModel(
            name="MeetingAttendance",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("peer_id", models.CharField(max_length=180)),
                ("joined_at", models.DateTimeField()),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                (
                    "meeting",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance",
                        to="meetings.meeting",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="meeting_attendance",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-joined_at",),
            },
        ),
        migrations.AddIndex(
            model_name="meetingattendance",
            index=models.Index(
                fields=["user", "joined_at"], name="meetings_me_user_id_9b7c7e_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="meetingattendance",
            index=models.Index(
                fields=["meeting", "user"], name="meetings_me_meeting_6a1a7a_idx"
            ),
        ),
    ]
