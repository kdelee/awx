from django.db import migrations, models


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        c.execute('ALTER TABLE main_job ADD COLUMN project_update_created timestamp with time zone')
        c.execute('ALTER TABLE main_inventoryupdate ADD COLUMN source_project_update_created timestamp with time zone')
        c.execute('ALTER TABLE main_workflowjobnode ADD COLUMN workflow_job_created timestamp with time zone')
        c.execute('UPDATE main_job j SET project_update_created=p.job_created FROM main_projectupdate p WHERE p.unifiedjob_ptr_id=j.project_update_id')
        c.execute('UPDATE main_inventoryupdate i SET source_project_update_created=p.job_created FROM main_projectupdate p WHERE p.unifiedjob_ptr_id=i.source_project_update_id')
        c.execute('UPDATE main_workflowjobnode n SET workflow_job_created=w.job_created FROM main_workflowjob w WHERE w.unifiedjob_ptr_id=n.workflow_job_id')
        c.execute('ALTER TABLE main_projectupdate ADD CONSTRAINT projectupdate_id_created_unique UNIQUE (unifiedjob_ptr_id,job_created)')
        c.execute('ALTER TABLE main_workflowjob ADD CONSTRAINT workflowjob_id_created_unique UNIQUE (unifiedjob_ptr_id,job_created)')
        refs = [('main_job','main_projectupdate','project_update_id','main_job_project_update_created_fk','project_update_created'), ('main_inventoryupdate','main_projectupdate','source_project_update_id','inventoryupdate_project_update_created_fk','source_project_update_created'), ('main_workflowjobnode','main_workflowjob','workflow_job_id','workflowjobnode_workflow_job_created_fk','workflow_job_created')]
        for table, parent, column, constraint, created in refs:
            c.execute("SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND confrelid=%s::regclass", [table,parent])
            for (old,) in c.fetchall(): c.execute(f'ALTER TABLE {table} DROP CONSTRAINT {old}')
            parent_id='unifiedjob_ptr_id'
            c.execute(f'ALTER TABLE {table} ADD CONSTRAINT {constraint} FOREIGN KEY ({column},{created}) REFERENCES {parent} ({parent_id},job_created) DEFERRABLE INITIALLY DEFERRED')
        # Remove duplicate id-only FKs where composite equivalents already exist.
        for table in ('main_jobhostsummary','main_indirectmanagednodeaudit','main_activitystream_job','main_activitystream_project_update','main_activitystream_workflow_job'):
            c.execute("SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND confrelid IN ('main_job'::regclass,'main_projectupdate'::regclass,'main_workflowjob'::regclass) AND array_length(conkey,1)=1", [table])
            for (old,) in c.fetchall(): c.execute(f'ALTER TABLE {table} DROP CONSTRAINT {old}')


class Migration(migrations.Migration):
    dependencies = [('main','0224_activitystream_execution_routing')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(forwards, migrations.RunPython.noop)],
            state_operations=[
                migrations.AddField(model_name='job', name='project_update_created', field=models.DateTimeField(default=None, editable=False, null=True)),
                migrations.AddField(model_name='inventoryupdate', name='source_project_update_created', field=models.DateTimeField(default=None, editable=False, null=True)),
                migrations.AddField(model_name='workflowjobnode', name='workflow_job_created', field=models.DateTimeField(default=None, editable=False, null=True)),
            ],
        )
    ]
