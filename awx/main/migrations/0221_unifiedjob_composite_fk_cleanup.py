from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    tables = ('main_unifiedjobtemplate','main_activitystream_unified_job','main_unifiedjob_dependent_jobs','main_unifiedjob_notifications','main_unifiedjob_labels','main_unifiedjob_credentials','main_joblaunchconfig','main_workflowjobnode','main_job','main_projectupdate','main_inventoryupdate','main_workflowjob','main_adhoccommand','main_workflowapproval','main_systemjob')
    with schema_editor.connection.cursor() as c:
        for table in tables:
            c.execute("SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND confrelid='main_unifiedjob'::regclass", [table])
            names = [row[0] for row in c.fetchall()]
            for name in names:
                if name not in {'activitystream_unifiedjob_created_fk','unifiedjob_dependent_from_fk','unifiedjob_dependent_to_fk','notifications_unifiedjob_created_fk','labels_unifiedjob_created_fk','credentials_unifiedjob_created_fk','joblaunchconfig_job_created_fk','workflowjobnode_job_created_fk','job_unifiedjob_created_fk','projectupdate_unifiedjob_created_fk','inventoryupdate_unifiedjob_created_fk','workflowjob_unifiedjob_created_fk','adhoccommand_unifiedjob_created_fk','workflowapproval_unifiedjob_created_fk','systemjob_unifiedjob_created_fk'}:
                    c.execute(f'ALTER TABLE {table} DROP CONSTRAINT {name}')
        c.execute('ALTER TABLE main_unifiedjobtemplate ADD CONSTRAINT ujt_current_job_created_fk FOREIGN KEY (current_job_id,current_job_created) REFERENCES main_unifiedjob(id,created) DEFERRABLE INITIALLY DEFERRED')
        c.execute('ALTER TABLE main_unifiedjobtemplate ADD CONSTRAINT ujt_last_job_created_fk FOREIGN KEY (last_job_id,last_job_created) REFERENCES main_unifiedjob(id,created) DEFERRABLE INITIALLY DEFERRED')


class Migration(migrations.Migration):
    dependencies = [('main','0220_unifiedjob_composite_foreign_keys')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
