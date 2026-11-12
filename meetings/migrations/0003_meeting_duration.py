from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("meetings", "0002_meeting_schedule_attendance")]
    operations = [
        migrations.AddField(
            model_name="meeting",
            name="duration_minutes",
            field=models.PositiveIntegerField(blank=True, null=True),
        )
    ]
