from django.db import migrations

EVENT_REFS = (
    ('_unpartitioned_main_jobevent', 'job_id', 'main_job', 'unifiedjob_ptr_id', 'job_created', 'jobevent_job_created_fk'),
    ('_unpartitioned_main_projectupdateevent', 'project_update_id', 'main_projectupdate', 'unifiedjob_ptr_id', 'job_created', 'projectupdateevent_job_created_fk'),
    ('_unpartitioned_main_inventoryupdateevent', 'inventory_update_id', 'main_inventoryupdate', 'unifiedjob_ptr_id', 'job_created', 'inventoryupdateevent_job_created_fk'),
    ('_unpartitioned_main_adhoccommandevent', 'ad_hoc_command_id', 'main_adhoccommand', 'unifiedjob_ptr_id', 'job_created', 'adhoccommandevent_job_created_fk'),
    ('_unpartitioned_main_systemjobevent', 'system_job_id', 'main_systemjob', 'unifiedjob_ptr_id', 'job_created', 'systemjobevent_job_created_fk'),
)


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        for event_table, event_id, child_table, child_id, child_created, constraint in EVENT_REFS:
            c.execute(f'ALTER TABLE {event_table} ADD COLUMN IF NOT EXISTS job_created timestamp with time zone')
            c.execute(f'UPDATE {event_table} e SET job_created = u.created FROM {child_table} child JOIN main_unifiedjob u ON u.id=child.unifiedjob_ptr_id WHERE child.unifiedjob_ptr_id=e.{event_id}')
            c.execute(f'ALTER TABLE {child_table} ADD CONSTRAINT {child_table}_id_created_unique UNIQUE ({child_id},{child_created})')
            c.execute(f"SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND confrelid=%s::regclass", [event_table, child_table])
            for (old,) in c.fetchall():
                c.execute(f'ALTER TABLE {event_table} DROP CONSTRAINT {old}')
            c.execute(f'ALTER TABLE {event_table} ADD CONSTRAINT {constraint} FOREIGN KEY ({event_id},job_created) REFERENCES {child_table} ({child_id},{child_created}) DEFERRABLE INITIALLY DEFERRED')


class Migration(migrations.Migration):
    dependencies = [('main', '0221_unifiedjob_composite_fk_cleanup')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
