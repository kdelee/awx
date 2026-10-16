from datetime import datetime, timezone

from django.db import migrations


def create_probe(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    epoch = datetime.now(timezone.utc).replace(microsecond=0)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS main_unifiedjob_partition_probe CASCADE')
        cursor.execute(
            'CREATE TABLE main_unifiedjob_partition_probe '
            '(LIKE main_unifiedjob INCLUDING DEFAULTS INCLUDING STORAGE) '
            'PARTITION BY RANGE (created)'
        )
        cursor.execute('ALTER TABLE main_unifiedjob_partition_probe DROP CONSTRAINT IF EXISTS main_unifiedjob_partition_probe_pkey')
        cursor.execute(
            'CREATE TABLE main_unifiedjob_partition_probe_before_epoch '
            'PARTITION OF main_unifiedjob_partition_probe '
            'FOR VALUES FROM (MINVALUE) TO (%s)',
            [epoch],
        )
        cursor.execute(
            'CREATE TABLE main_unifiedjob_partition_probe_after_epoch '
            'PARTITION OF main_unifiedjob_partition_probe '
            'FOR VALUES FROM (%s) TO (MAXVALUE)',
            [epoch],
        )
        cursor.execute(
            'ALTER TABLE main_unifiedjob_partition_probe '
            'ADD CONSTRAINT main_unifiedjob_partition_probe_pkey PRIMARY KEY (id, created)'
        )
        cursor.execute('INSERT INTO main_unifiedjob_partition_probe SELECT * FROM main_unifiedjob')


def drop_probe(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS main_unifiedjob_partition_probe CASCADE')


class Migration(migrations.Migration):
    dependencies = [('main', '0213_unified_job_created_date_summary')]
    operations = [migrations.RunPython(create_probe, drop_probe)]
