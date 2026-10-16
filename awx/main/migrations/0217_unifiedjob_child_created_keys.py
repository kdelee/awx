from django.db import migrations, models


CHILDREN = ('job', 'projectupdate', 'inventoryupdate', 'workflowjob', 'adhoccommand', 'workflowapproval', 'systemjob')


def backfill_job_created(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        for child in CHILDREN:
            cursor.execute(
                f'UPDATE main_{child} c SET job_created = u.created '
                'FROM main_unifiedjob u WHERE u.id = c.unifiedjob_ptr_id'
            )
            cursor.execute(f'ALTER TABLE main_{child} ALTER COLUMN job_created SET NOT NULL')
            cursor.execute(
                f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM main_{child} c JOIN main_unifiedjob u ON u.id = c.unifiedjob_ptr_id WHERE c.job_created <> u.created) THEN RAISE EXCEPTION 'job_created mismatch in main_{child}'; END IF; END $$"
            )


class Migration(migrations.Migration):
    dependencies = [('main', '0216_unifiedjob_child_partition_probes')]
    operations = [
        migrations.AddField(model_name='job', name='job_created', field=models.DateTimeField(editable=False, null=True)),
        migrations.AddField(model_name='projectupdate', name='job_created', field=models.DateTimeField(editable=False, null=True)),
        migrations.AddField(model_name='inventoryupdate', name='job_created', field=models.DateTimeField(editable=False, null=True)),
        migrations.AddField(model_name='workflowjob', name='job_created', field=models.DateTimeField(editable=False, null=True)),
        migrations.AddField(model_name='adhoccommand', name='job_created', field=models.DateTimeField(editable=False, null=True)),
        migrations.AddField(model_name='workflowapproval', name='job_created', field=models.DateTimeField(editable=False, null=True)),
        migrations.AddField(model_name='systemjob', name='job_created', field=models.DateTimeField(editable=False, null=True)),
        migrations.RunPython(backfill_job_created, migrations.RunPython.noop),
    ]
