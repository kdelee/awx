import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('main', '0214_unifiedjob_child_created_keys')]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE main_activitystream_unified_job ADD COLUMN unifiedjob_created timestamp with time zone",
                    "ALTER TABLE main_activitystream_unified_job DROP COLUMN unifiedjob_created",
                ),
                migrations.RunSQL(
                    "UPDATE main_activitystream_unified_job r SET unifiedjob_created = u.created FROM main_unifiedjob u WHERE u.id = r.unifiedjob_id",
                    migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    "ALTER TABLE main_activitystream_unified_job ALTER COLUMN unifiedjob_created SET NOT NULL",
                    migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    "ALTER TABLE main_unifiedjob ADD CONSTRAINT unifiedjob_id_created_unique UNIQUE (id, created)",
                    "ALTER TABLE main_unifiedjob DROP CONSTRAINT IF EXISTS unifiedjob_id_created_unique",
                ),
                migrations.RunSQL(
                    "ALTER TABLE main_activitystream_unified_job ADD CONSTRAINT activitystream_unifiedjob_created_fk FOREIGN KEY (unifiedjob_id, unifiedjob_created) REFERENCES main_unifiedjob (id, created) DEFERRABLE INITIALLY DEFERRED",
                    "ALTER TABLE main_activitystream_unified_job DROP CONSTRAINT IF EXISTS activitystream_unifiedjob_created_fk",
                ),
                migrations.RunSQL(
                    "CREATE INDEX activitystream_uj_created_idx ON main_activitystream_unified_job (unifiedjob_id, unifiedjob_created)",
                    "DROP INDEX IF EXISTS activitystream_uj_created_idx",
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='ActivityStreamUnifiedJob',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('unified_job_created', models.DateTimeField(editable=False)),
                        ('activity_stream', models.ForeignKey(db_column='activitystream_id', on_delete=django.db.models.deletion.CASCADE, to='main.activitystream')),
                        ('unified_job', models.ForeignKey(db_column='unifiedjob_id', on_delete=django.db.models.deletion.CASCADE, to='main.unifiedjob')),
                    ],
                    options={'db_table': 'main_activitystream_unified_job'},
                ),
                migrations.AlterField(
                    model_name='activitystream',
                    name='unified_job',
                    field=models.ManyToManyField(blank=True, related_name='activity_stream_as_unified_job+', through='main.ActivityStreamUnifiedJob', to='main.unifiedjob'),
                ),
                migrations.AddConstraint(
                    model_name='unifiedjob',
                    constraint=models.UniqueConstraint(fields=('id', 'created'), name='unifiedjob_id_created_unique'),
                ),
                migrations.AddIndex(
                    model_name='activitystreamunifiedjob',
                    index=models.Index(fields=['unified_job', 'unified_job_created'], name='activitystream_uj_created_idx'),
                ),
                migrations.AddConstraint(
                    model_name='activitystreamunifiedjob',
                    constraint=models.UniqueConstraint(fields=('activity_stream', 'unified_job'), name='activitystream_unifiedjob_unique'),
                ),
            ],
        )
    ]
