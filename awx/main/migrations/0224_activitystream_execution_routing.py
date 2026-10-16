from django.db import migrations, models
import django.db.models.deletion

RELATIONS = (
    ('main_activitystream_job', 'job_id', 'main_job', 'job_created', 'activitystream_job_created_fk'),
    ('main_activitystream_project_update', 'projectupdate_id', 'main_projectupdate', 'job_created', 'activitystream_projectupdate_created_fk'),
    ('main_activitystream_inventory_update', 'inventoryupdate_id', 'main_inventoryupdate', 'job_created', 'activitystream_inventoryupdate_created_fk'),
    ('main_activitystream_workflow_job', 'workflowjob_id', 'main_workflowjob', 'job_created', 'activitystream_workflowjob_created_fk'),
    ('main_activitystream_workflow_approval', 'workflowapproval_id', 'main_workflowapproval', 'job_created', 'activitystream_workflowapproval_created_fk'),
    ('main_activitystream_ad_hoc_command', 'adhoccommand_id', 'main_adhoccommand', 'job_created', 'activitystream_adhoccommand_created_fk'),
)


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        for table, execution_id, execution_table, execution_created, constraint in RELATIONS:
            c.execute(f'ALTER TABLE {table} ADD COLUMN unifiedjob_created timestamp with time zone')
            c.execute(f'UPDATE {table} r SET unifiedjob_created=u.created FROM {execution_table} e JOIN main_unifiedjob u ON u.id=e.unifiedjob_ptr_id WHERE e.unifiedjob_ptr_id=r.{execution_id}')
            c.execute(f'ALTER TABLE {table} ALTER COLUMN unifiedjob_created SET NOT NULL')
            c.execute("SELECT 1 FROM pg_constraint WHERE conrelid=%s::regclass AND contype='u' AND conkey=(SELECT array_agg(attnum ORDER BY attnum) FROM pg_attribute WHERE attrelid=%s::regclass AND attname IN ('unifiedjob_ptr_id','job_created'))", [execution_table, execution_table])
            if not c.fetchone():
                c.execute(f'ALTER TABLE {execution_table} ADD CONSTRAINT {execution_table}_id_created_unique UNIQUE (unifiedjob_ptr_id,job_created)')
            c.execute(f'ALTER TABLE {table} ADD CONSTRAINT {constraint} FOREIGN KEY ({execution_id},unifiedjob_created) REFERENCES {execution_table} (unifiedjob_ptr_id,{execution_created}) DEFERRABLE INITIALLY DEFERRED')
            c.execute(f'CREATE INDEX {constraint}_idx ON {table} ({execution_id},unifiedjob_created)')


class Migration(migrations.Migration):
    dependencies = [('main', '0223_indirectmanagednodeaudit_job_created_and_more')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(forwards, migrations.RunPython.noop)],
            state_operations=[
                migrations.CreateModel(name='ActivityStreamJob', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('unified_job_created', models.DateTimeField(null=True, editable=False, db_column='unifiedjob_created')), ('activity_stream', models.ForeignKey(db_column='activitystream_id', on_delete=django.db.models.deletion.CASCADE, to='main.activitystream')), ('job', models.ForeignKey(db_column='job_id', on_delete=django.db.models.deletion.CASCADE, to='main.job'))], options={'db_table': 'main_activitystream_job'}),
                migrations.CreateModel(name='ActivityStreamProjectUpdate', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('unified_job_created', models.DateTimeField(null=True, editable=False, db_column='unifiedjob_created')), ('activity_stream', models.ForeignKey(db_column='activitystream_id', on_delete=django.db.models.deletion.CASCADE, to='main.activitystream')), ('project_update', models.ForeignKey(db_column='projectupdate_id', on_delete=django.db.models.deletion.CASCADE, to='main.projectupdate'))], options={'db_table': 'main_activitystream_project_update'}),
                migrations.CreateModel(name='ActivityStreamInventoryUpdate', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('unified_job_created', models.DateTimeField(null=True, editable=False, db_column='unifiedjob_created')), ('activity_stream', models.ForeignKey(db_column='activitystream_id', on_delete=django.db.models.deletion.CASCADE, to='main.activitystream')), ('inventory_update', models.ForeignKey(db_column='inventoryupdate_id', on_delete=django.db.models.deletion.CASCADE, to='main.inventoryupdate'))], options={'db_table': 'main_activitystream_inventory_update'}),
                migrations.CreateModel(name='ActivityStreamWorkflowJob', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('unified_job_created', models.DateTimeField(null=True, editable=False, db_column='unifiedjob_created')), ('activity_stream', models.ForeignKey(db_column='activitystream_id', on_delete=django.db.models.deletion.CASCADE, to='main.activitystream')), ('workflow_job', models.ForeignKey(db_column='workflowjob_id', on_delete=django.db.models.CASCADE, to='main.workflowjob'))], options={'db_table': 'main_activitystream_workflow_job'}),
                migrations.CreateModel(name='ActivityStreamWorkflowApproval', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('unified_job_created', models.DateTimeField(null=True, editable=False, db_column='unifiedjob_created')), ('activity_stream', models.ForeignKey(db_column='activitystream_id', on_delete=django.db.models.CASCADE, to='main.activitystream')), ('workflow_approval', models.ForeignKey(db_column='workflowapproval_id', on_delete=django.db.models.CASCADE, to='main.workflowapproval'))], options={'db_table': 'main_activitystream_workflow_approval'}),
                migrations.CreateModel(name='ActivityStreamAdHocCommand', fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('unified_job_created', models.DateTimeField(null=True, editable=False, db_column='unifiedjob_created')), ('activity_stream', models.ForeignKey(db_column='activitystream_id', on_delete=django.db.models.CASCADE, to='main.activitystream')), ('ad_hoc_command', models.ForeignKey(db_column='adhoccommand_id', on_delete=django.db.models.CASCADE, to='main.adhoccommand'))], options={'db_table': 'main_activitystream_ad_hoc_command'}),
                migrations.AlterField(model_name='activitystream', name='job', field=models.ManyToManyField(blank=True, through='main.ActivityStreamJob', to='main.job')),
                migrations.AlterField(model_name='activitystream', name='project_update', field=models.ManyToManyField(blank=True, through='main.ActivityStreamProjectUpdate', to='main.projectupdate')),
                migrations.AlterField(model_name='activitystream', name='inventory_update', field=models.ManyToManyField(blank=True, through='main.ActivityStreamInventoryUpdate', to='main.inventoryupdate')),
                migrations.AlterField(model_name='activitystream', name='workflow_job', field=models.ManyToManyField(blank=True, through='main.ActivityStreamWorkflowJob', to='main.workflowjob')),
                migrations.AlterField(model_name='activitystream', name='workflow_approval', field=models.ManyToManyField(blank=True, through='main.ActivityStreamWorkflowApproval', to='main.workflowapproval')),
                migrations.AlterField(model_name='activitystream', name='ad_hoc_command', field=models.ManyToManyField(blank=True, through='main.ActivityStreamAdHocCommand', to='main.adhoccommand')),
            ],
        )
    ]
