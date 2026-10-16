from django.db import migrations


COMPOSITE = (
    ('main_unifiedjobtemplate', 'current_job_id', 'current_job_created', 'ujt_current_job_created_fk'),
    ('main_unifiedjobtemplate', 'last_job_id', 'last_job_created', 'ujt_last_job_created_fk'),
    ('main_activitystream_unified_job', 'unifiedjob_id', 'unifiedjob_created', 'activitystream_unifiedjob_created_fk'),
    ('main_unifiedjob_dependent_jobs', 'from_unifiedjob_id', 'from_unifiedjob_created', 'unifiedjob_dependent_from_fk'),
    ('main_unifiedjob_dependent_jobs', 'to_unifiedjob_id', 'to_unifiedjob_created', 'unifiedjob_dependent_to_fk'),
    ('main_unifiedjob_notifications', 'unifiedjob_id', 'unifiedjob_created', 'unifiedjob_notifications_created_fk'),
    ('main_unifiedjob_labels', 'unifiedjob_id', 'unifiedjob_created', 'unifiedjob_labels_created_fk'),
    ('main_unifiedjob_credentials', 'unifiedjob_id', 'unifiedjob_created', 'unifiedjob_credentials_created_fk'),
    ('main_joblaunchconfig', 'job_id', 'job_created', 'joblaunchconfig_job_created_fk'),
    ('main_workflowjobnode', 'job_id', 'job_created', 'workflowjobnode_job_created_fk'),
    ('main_job', 'unifiedjob_ptr_id', 'job_created', 'job_unifiedjob_created_fk'),
    ('main_projectupdate', 'unifiedjob_ptr_id', 'job_created', 'projectupdate_unifiedjob_created_fk'),
    ('main_inventoryupdate', 'unifiedjob_ptr_id', 'job_created', 'inventoryupdate_unifiedjob_created_fk'),
    ('main_workflowjob', 'unifiedjob_ptr_id', 'job_created', 'workflowjob_unifiedjob_created_fk'),
    ('main_adhoccommand', 'unifiedjob_ptr_id', 'job_created', 'adhoccommand_unifiedjob_created_fk'),
    ('main_workflowapproval', 'unifiedjob_ptr_id', 'job_created', 'workflowapproval_unifiedjob_created_fk'),
    ('main_systemjob', 'unifiedjob_ptr_id', 'job_created', 'systemjob_unifiedjob_created_fk'),
)


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        for table, column, created_column, constraint in COMPOSITE:
            c.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND confrelid='main_unifiedjob'::regclass",
                [table],
            )
            for (old_constraint,) in c.fetchall():
                c.execute(f'ALTER TABLE {table} DROP CONSTRAINT {old_constraint}')
            c.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}')
            nullable = table in {'main_unifiedjobtemplate', 'main_workflowjobnode'}
            if nullable:
                condition = f'CHECK (({column} IS NULL AND {created_column} IS NULL) OR ({column} IS NOT NULL AND {created_column} IS NOT NULL))'
                c.execute(f'ALTER TABLE {table} ADD CONSTRAINT {constraint}_presence {condition}')
            c.execute(f'ALTER TABLE {table} ADD CONSTRAINT {constraint} FOREIGN KEY ({column}, {created_column}) REFERENCES main_unifiedjob (id, created) DEFERRABLE INITIALLY DEFERRED')


def backwards(apps, schema_editor):
    raise RuntimeError('Composite UnifiedJob foreign keys require restoring the pre-0220 schema from backup')


class Migration(migrations.Migration):
    dependencies = [('main', '0219_unifiedjob_relationship_routing')]
    operations = [migrations.RunPython(forwards, backwards)]
