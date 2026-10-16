import django.db.models.deletion
from django.db import migrations, models

TABLES = {
    'credentials': ('main_unifiedjob_credentials', 'credential_id', 'UnifiedJobCredential', 'Credential', 'uj_credential_created_idx', 'unifiedjob_credential_unique'),
    'labels': ('main_unifiedjob_labels', 'label_id', 'UnifiedJobLabel', 'Label', 'uj_label_created_idx', 'unifiedjob_label_unique'),
    'notifications': ('main_unifiedjob_notifications', 'notification_id', 'UnifiedJobNotification', 'Notification', 'uj_notification_created_idx', 'unifiedjob_notification_unique'),
}


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        for relation, (table, related_column, _, _, index, unique) in TABLES.items():
            c.execute(f'ALTER TABLE {table} ADD COLUMN unifiedjob_created timestamp with time zone')
            c.execute(f'UPDATE {table} r SET unifiedjob_created=u.created FROM main_unifiedjob u WHERE u.id=r.unifiedjob_id')
            c.execute(f"SELECT count(*) FROM {table} WHERE unifiedjob_created IS NULL")
            if c.fetchone()[0]:
                raise RuntimeError(f'{table} routing backfill incomplete')
            c.execute(f'ALTER TABLE {table} ALTER COLUMN unifiedjob_created SET NOT NULL')
            c.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_unifiedjob_id_fkey')
            c.execute(f'ALTER TABLE {table} ADD CONSTRAINT {relation}_unifiedjob_created_fk FOREIGN KEY (unifiedjob_id,unifiedjob_created) REFERENCES main_unifiedjob(id,created) DEFERRABLE INITIALLY DEFERRED')
            c.execute(f'CREATE INDEX {index} ON {table} (unifiedjob_id,unifiedjob_created)')


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        for relation, (table, _, _, _, index, _) in TABLES.items():
            c.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {relation}_unifiedjob_created_fk')
            c.execute(f'DROP INDEX IF EXISTS {index}')
            c.execute(f'ALTER TABLE {table} DROP COLUMN unifiedjob_created')


class Migration(migrations.Migration):
    dependencies = [('main', '0218_unifiedjobdependent_through_routing')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(forwards, backwards)],
            state_operations=[
                migrations.CreateModel(name='UnifiedJobCredential', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('unified_job_created', models.DateTimeField(editable=False)), ('credential', models.ForeignKey(db_column='credential_id', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='main.credential')), ('unified_job', models.ForeignKey(db_column='unifiedjob_id', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='main.unifiedjob'))], options={'db_table': 'main_unifiedjob_credentials'}),
                migrations.AlterField(model_name='unifiedjob', name='credentials', field=models.ManyToManyField(related_name='%(class)ss', through='main.UnifiedJobCredential', to='main.credential')),
                migrations.CreateModel(name='UnifiedJobLabel', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('unified_job_created', models.DateTimeField(editable=False)), ('label', models.ForeignKey(db_column='label_id', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='main.label')), ('unified_job', models.ForeignKey(db_column='unifiedjob_id', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='main.unifiedjob'))], options={'db_table': 'main_unifiedjob_labels'}),
                migrations.AlterField(model_name='unifiedjob', name='labels', field=models.ManyToManyField(blank=True, related_name='%(class)s_labels', through='main.UnifiedJobLabel', to='main.label')),
                migrations.CreateModel(name='UnifiedJobNotification', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('unified_job_created', models.DateTimeField(editable=False)), ('notification', models.ForeignKey(db_column='notification_id', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='main.notification')), ('unified_job', models.ForeignKey(db_column='unifiedjob_id', on_delete=django.db.models.CASCADE, related_name='+', to='main.unifiedjob'))], options={'db_table': 'main_unifiedjob_notifications'}),
                migrations.AlterField(model_name='unifiedjob', name='notifications', field=models.ManyToManyField(editable=False, related_name='%(class)s_notifications', through='main.UnifiedJobNotification', to='main.notification')),
                migrations.AddIndex(model_name='unifiedjobcredential', index=models.Index(fields=['unified_job','unified_job_created'], name='uj_credential_created_idx')),
                migrations.AddIndex(model_name='unifiedjoblabel', index=models.Index(fields=['unified_job','unified_job_created'], name='uj_label_created_idx')),
                migrations.AddIndex(model_name='unifiedjobnotification', index=models.Index(fields=['unified_job','unified_job_created'], name='uj_notification_created_idx')),
                migrations.AddConstraint(model_name='unifiedjobcredential', constraint=models.UniqueConstraint(fields=('unified_job','credential'), name='unifiedjob_credential_unique')),
                migrations.AddConstraint(model_name='unifiedjoblabel', constraint=models.UniqueConstraint(fields=('unified_job','label'), name='unifiedjob_label_unique')),
                migrations.AddConstraint(model_name='unifiedjobnotification', constraint=models.UniqueConstraint(fields=('unified_job','notification'), name='unifiedjob_notification_unique')),
            ],
        )
    ]
