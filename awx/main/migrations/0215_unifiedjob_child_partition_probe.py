from datetime import datetime, timezone

from django.db import migrations


def create_probe(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    epoch = datetime.now(timezone.utc).replace(microsecond=0)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS main_job_partition_probe CASCADE')
        cursor.execute(
            'CREATE TABLE main_job_partition_probe '
            '(LIKE main_job INCLUDING DEFAULTS INCLUDING STORAGE, created timestamptz NOT NULL) '
            'PARTITION BY RANGE (created)'
        )
        cursor.execute('ALTER TABLE main_job_partition_probe DROP CONSTRAINT IF EXISTS main_job_partition_probe_pkey')
        cursor.execute(
            'CREATE TABLE main_job_partition_probe_before_epoch PARTITION OF main_job_partition_probe '
            'FOR VALUES FROM (MINVALUE) TO (%s)', [epoch]
        )
        cursor.execute(
            'CREATE TABLE main_job_partition_probe_after_epoch PARTITION OF main_job_partition_probe '
            'FOR VALUES FROM (%s) TO (MAXVALUE)', [epoch]
        )
        cursor.execute(
            'ALTER TABLE main_job_partition_probe ADD CONSTRAINT main_job_partition_probe_pkey '
            'PRIMARY KEY (unifiedjob_ptr_id, created)'
        )
        cursor.execute(
            'INSERT INTO main_job_partition_probe '
            'SELECT j.*, u.created FROM main_job j JOIN main_unifiedjob u ON u.id = j.unifiedjob_ptr_id'
        )
        cursor.execute(
            'ALTER TABLE main_job_partition_probe ADD CONSTRAINT main_job_partition_probe_unifiedjob_fk '
            'FOREIGN KEY (unifiedjob_ptr_id, created) '
            'REFERENCES main_unifiedjob_partition_probe (id, created) '
            'DEFERRABLE INITIALLY DEFERRED'
        )


def drop_probe(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS main_job_partition_probe CASCADE')


class Migration(migrations.Migration):
    dependencies = [('main', '0214_unifiedjob_partition_probe')]
    operations = [migrations.RunPython(create_probe, drop_probe)]
