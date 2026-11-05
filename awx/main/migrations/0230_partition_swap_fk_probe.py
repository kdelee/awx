from django.db import migrations

CHILDREN=('main_job','main_projectupdate','main_inventoryupdate','main_workflowjob','main_adhoccommand','main_workflowapproval','main_systemjob')

def forwards(apps,schema_editor):
    if schema_editor.connection.vendor!='postgresql': return
    with schema_editor.connection.cursor() as c:
        for table in CHILDREN:
            c.execute(f'ALTER TABLE {table} ADD CONSTRAINT {table}_partition_parent_fk FOREIGN KEY (unifiedjob_ptr_id,job_created) REFERENCES main_unifiedjob(id,created) DEFERRABLE INITIALLY DEFERRED')
        c.execute('SELECT count(*) FROM main_unifiedjob')
        parent=c.fetchone()[0]
        c.execute('SELECT count(*) FROM main_job')
        child=c.fetchone()[0]
        if child>parent: raise RuntimeError('child rows exceed parent rows')

class Migration(migrations.Migration):
    dependencies=[('main','0229_partition_swap_indexes_probe')]
    operations=[migrations.RunPython(forwards,migrations.RunPython.noop)]
