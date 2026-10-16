from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        c.execute("SELECT conname FROM pg_constraint WHERE conrelid='main_workflowjobinstancegroupmembership'::regclass AND confrelid='main_workflowjob'::regclass AND array_length(conkey,1)=1")
        for (name,) in c.fetchall():
            c.execute(f'ALTER TABLE main_workflowjobinstancegroupmembership DROP CONSTRAINT {name}')


class Migration(migrations.Migration):
    dependencies = [('main', '0226_workflowjob_instancegroup_routing')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
