from django.db import migrations, models


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        c.execute('ALTER TABLE main_workflowjobinstancegroupmembership ADD COLUMN workflowjob_created timestamp with time zone')
        c.execute('UPDATE main_workflowjobinstancegroupmembership m SET workflowjob_created=w.job_created FROM main_workflowjob w WHERE w.unifiedjob_ptr_id=m.workflowjobnode_id')
        c.execute('ALTER TABLE main_workflowjobinstancegroupmembership ALTER COLUMN workflowjob_created SET NOT NULL')
        c.execute('ALTER TABLE main_workflowjobinstancegroupmembership ADD CONSTRAINT workflowjob_ig_created_fk FOREIGN KEY (workflowjobnode_id,workflowjob_created) REFERENCES main_workflowjob(unifiedjob_ptr_id,job_created) DEFERRABLE INITIALLY DEFERRED')
        c.execute('CREATE INDEX workflowjob_ig_created_idx ON main_workflowjobinstancegroupmembership (workflowjobnode_id,workflowjob_created)')


class Migration(migrations.Migration):
    dependencies = [('main', '0225_cross_child_composite_foreign_keys')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(forwards, migrations.RunPython.noop)],
            state_operations=[migrations.AddField(model_name='workflowjobinstancegroupmembership', name='workflowjob_created', field=models.DateTimeField(default=None, editable=False, null=True))],
        )
    ]
