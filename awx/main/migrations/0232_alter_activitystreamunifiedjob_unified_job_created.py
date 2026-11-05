from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('main', '0231_restore_probe_foreign_keys')]
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.AlterField(
                model_name='activitystreamunifiedjob',
                name='unified_job_created',
                field=models.DateTimeField(db_column='unifiedjob_created', editable=False),
            )],
            database_operations=[],
        ),
    ]
