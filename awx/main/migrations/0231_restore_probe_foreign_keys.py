from django.db import migrations

FKS = (
 ('main_unifiedjobtemplate','current_job_id,current_job_created','main_unifiedjob','id,created','probe_ujt_current_fk'),
 ('main_unifiedjobtemplate','last_job_id,last_job_created','main_unifiedjob','id,created','probe_ujt_last_fk'),
 ('main_unifiedjob_dependent_jobs','from_unifiedjob_id,from_unifiedjob_created','main_unifiedjob','id,created','probe_dep_from_fk'),
 ('main_unifiedjob_dependent_jobs','to_unifiedjob_id,to_unifiedjob_created','main_unifiedjob','id,created','probe_dep_to_fk'),
 ('main_activitystream_unified_job','unifiedjob_id,unifiedjob_created','main_unifiedjob','id,created','probe_as_uj_fk'),
 ('main_unifiedjob_notifications','unifiedjob_id,unifiedjob_created','main_unifiedjob','id,created','probe_notifications_fk'),
 ('main_unifiedjob_labels','unifiedjob_id,unifiedjob_created','main_unifiedjob','id,created','probe_labels_fk'),
 ('main_unifiedjob_credentials','unifiedjob_id,unifiedjob_created','main_unifiedjob','id,created','probe_credentials_fk'),
 ('main_joblaunchconfig','job_id,job_created','main_unifiedjob','id,created','probe_launch_fk'),
 ('main_workflowjobnode','job_id,job_created','main_unifiedjob','id,created','probe_node_job_fk'),
)

def forwards(apps,schema_editor):
    if schema_editor.connection.vendor!='postgresql': return
    with schema_editor.connection.cursor() as c:
        for table, column, parent, created, name in (
            ('main_activitystream_job','job_id','main_job','job_created','restore_as_job_fk'),
            ('main_activitystream_project_update','projectupdate_id','main_projectupdate','job_created','restore_as_pu_fk'),
            ('main_activitystream_inventory_update','inventoryupdate_id','main_inventoryupdate','job_created','restore_as_iu_fk'),
            ('main_activitystream_workflow_job','workflowjob_id','main_workflowjob','job_created','restore_as_wj_fk'),
            ('main_activitystream_workflow_approval','workflowapproval_id','main_workflowapproval','job_created','restore_as_wa_fk'),
            ('main_activitystream_ad_hoc_command','adhoccommand_id','main_adhoccommand','job_created','restore_as_ahc_fk'),
        ):
            c.execute('SELECT 1 FROM pg_constraint WHERE conname=%s', [name])
            if c.fetchone() is None:
                c.execute(f'ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY ({column},unifiedjob_created) REFERENCES {parent} (unifiedjob_ptr_id,{created}) DEFERRABLE INITIALLY DEFERRED')
        c.execute('UPDATE main_joblaunchconfig c SET job_created=u.created FROM main_unifiedjob u WHERE u.id=c.job_id')
        c.execute('UPDATE main_workflowjobnode c SET job_created=u.created FROM main_unifiedjob u WHERE u.id=c.job_id')
        c.execute('UPDATE main_unifiedjobtemplate t SET current_job_created=u.created FROM main_unifiedjob u WHERE u.id=t.current_job_id')
        c.execute('UPDATE main_unifiedjobtemplate t SET last_job_created=u.created FROM main_unifiedjob u WHERE u.id=t.last_job_id')
        c.execute("SELECT r.conrelid::regclass::text, r.conname, pg_get_constraintdef(r.oid) FROM pg_constraint r WHERE r.oid IN (SELECT conparentid FROM pg_constraint WHERE confrelid::regclass::text LIKE '_probe_main_%' AND conparentid <> 0)")
        for table, name, definition in c.fetchall():
            c.execute(f'ALTER TABLE {table} DROP CONSTRAINT {name}')
            definition = definition.replace('_probe_main_', 'main_')
            c.execute(f'ALTER TABLE {table} ADD CONSTRAINT {name} {definition}')
        c.execute("SELECT child_table, constraint_name, definition FROM _partition_fk_metadata")
        for table, name, definition in c.fetchall():
            definition = definition.replace('_probe_main_', 'main_')
            c.execute('SELECT 1 FROM pg_constraint WHERE conname=%s', [name])
            if c.fetchone() is None:
                # Earlier routing migrations replaced id-only execution FKs.
                c.execute("SELECT 1 FROM pg_constraint x WHERE x.conrelid=%s::regclass AND x.contype='f' AND pg_get_constraintdef(x.oid) LIKE '%%job_created%%'", [table])
                if c.fetchone() is not None and 'job_created' not in definition:
                    continue
                if 'job_created' not in definition and any(f'REFERENCES {parent}(unifiedjob_ptr_id)' in definition for parent in ('main_job','main_projectupdate','main_inventoryupdate','main_workflowjob','main_workflowapproval','main_adhoccommand','main_systemjob')):
                    continue
                try:
                    c.execute(f'ALTER TABLE {table} ADD CONSTRAINT {name} {definition}')
                except Exception as exc:
                    raise RuntimeError(f'cannot restore {name} on {table}: {definition}') from exc
        c.execute('DROP TABLE _partition_fk_metadata')

class Migration(migrations.Migration):
    dependencies=[('main','0230_partition_swap_fk_probe')]
    operations=[migrations.RunPython(forwards,migrations.RunPython.noop)]
