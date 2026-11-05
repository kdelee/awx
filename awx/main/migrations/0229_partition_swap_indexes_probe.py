from django.db import migrations

TABLES=('main_unifiedjob','main_job','main_projectupdate','main_inventoryupdate','main_workflowjob','main_adhoccommand','main_workflowapproval','main_systemjob')

def forwards(apps,schema_editor):
    if schema_editor.connection.vendor!='postgresql': return
    with schema_editor.connection.cursor() as c:
        for table in TABLES:
            old=f'_probe_{table}'
            c.execute("SELECT indexrelid::regclass::text, pg_get_indexdef(indexrelid) FROM pg_index WHERE indrelid=%s::regclass AND NOT indisprimary AND NOT indisunique",[old])
            for name,definition in c.fetchall():
                new_name=f'partitioned_{name}'[:63]
                definition=definition.replace(name,new_name,1).replace(old,table)
                c.execute(definition)

class Migration(migrations.Migration):
    dependencies=[('main','0228_partition_swap_probe')]
    operations=[migrations.RunPython(forwards,migrations.RunPython.noop)]
