from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0003_meeting_duration'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='meeting',
            new_name='meetings_me_host_id_97f21e_idx',
            old_name='meetings_me_host_i_4e2e20_idx',
        ),
        migrations.RenameIndex(
            model_name='meeting',
            new_name='meetings_me_schedul_84025c_idx',
            old_name='meetings_me_schedu_4f2b0c_idx',
        ),
        migrations.RenameIndex(
            model_name='meetingattendance',
            new_name='meetings_me_user_id_522d22_idx',
            old_name='meetings_me_user_id_9b7c7e_idx',
        ),
        migrations.RenameIndex(
            model_name='meetingattendance',
            new_name='meetings_me_meeting_cc2705_idx',
            old_name='meetings_me_meeting_6a1a7a_idx',
        ),
    ]
