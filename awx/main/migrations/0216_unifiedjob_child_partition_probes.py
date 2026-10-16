from datetime import datetime, timezone

from django.db import migrations


CHILDREN = ('projectupdate', 'inventoryupdate')


def create_probes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    epoch = datetime.now(timezone.utc).replace(microsecond=0)
    with schema_editor.connection.cursor() as cursor:
        for child in CHILDREN:
            source = f'main_{child}'
            probe = f'{source}_partition_probe'
            cursor.execute(f'DROP TABLE IF EXISTS {probe} CASCADE')
            cursor.execute(
                f'CREATE TABLE {probe} (LIKE {source} INCLUDING DEFAULTS INCLUDING STORAGE, created timestamptz NOT NULL) '
                'PARTITION BY RANGE (created)'
            )
            cursor.execute(f'ALTER TABLE {probe} DROP CONSTRAINT IF EXISTS {probe}_pkey')
            cursor.execute(
                f'CREATE TABLE {probe}_before_epoch PARTITION OF {probe} FOR VALUES FROM (MINVALUE) TO (%s)', [epoch]
            )
            cursor.execute(
                f'CREATE TABLE {probe}_after_epoch PARTITION OF {probe} FOR VALUES FROM (%s) TO (MAXVALUE)', [epoch]
            )
            cursor.execute(f'ALTER TABLE {probe} ADD CONSTRAINT {probe}_pkey PRIMARY KEY (unifiedjob_ptr_id, created)')
            cursor.execute(
                f'INSERT INTO {probe} SELECT c.*, u.created FROM {source} c '
                f'JOIN main_unifiedjob u ON u.id = c.unifiedjob_ptr_id'
            )
            cursor.execute(
                f'ALTER TABLE {probe} ADD CONSTRAINT {probe}_unifiedjob_fk '
                f'FOREIGN KEY (unifiedjob_ptr_id, created) REFERENCES main_unifiedjob_partition_probe (id, created) '
                'DEFERRABLE INITIALLY DEFERRED'
            )


def drop_probes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        for child in CHILDREN:
            cursor.execute(f'DROP TABLE IF EXISTS main_{child}_partition_probe CASCADE')


class Migration(migrations.Migration):
    dependencies = [('main', '0215_unifiedjob_child_partition_probe')]
    operations = [migrations.RunPython(create_probes, drop_probes)]
