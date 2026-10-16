from django.db import migrations, models
import django.db.models.deletion


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs ADD COLUMN from_unifiedjob_created timestamp with time zone')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs ADD COLUMN to_unifiedjob_created timestamp with time zone')
        c.execute('UPDATE main_unifiedjob_dependent_jobs r SET from_unifiedjob_created=u.created FROM main_unifiedjob u WHERE u.id=r.from_unifiedjob_id')
        c.execute('UPDATE main_unifiedjob_dependent_jobs r SET to_unifiedjob_created=u.created FROM main_unifiedjob u WHERE u.id=r.to_unifiedjob_id')
        c.execute("SELECT count(*) FROM main_unifiedjob_dependent_jobs WHERE from_unifiedjob_created IS NULL OR to_unifiedjob_created IS NULL")
        if c.fetchone()[0]:
            raise RuntimeError('unified job dependency routing backfill incomplete')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs ALTER COLUMN from_unifiedjob_created SET NOT NULL')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs ALTER COLUMN to_unifiedjob_created SET NOT NULL')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs DROP CONSTRAINT IF EXISTS main_unifiedjob_dependent_jobs_from_unifiedjob_id_fkey')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs DROP CONSTRAINT IF EXISTS main_unifiedjob_dependent_jobs_to_unifiedjob_id_fkey')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs ADD CONSTRAINT unifiedjob_dependent_from_fk FOREIGN KEY (from_unifiedjob_id,from_unifiedjob_created) REFERENCES main_unifiedjob(id,created) DEFERRABLE INITIALLY DEFERRED')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs ADD CONSTRAINT unifiedjob_dependent_to_fk FOREIGN KEY (to_unifiedjob_id,to_unifiedjob_created) REFERENCES main_unifiedjob(id,created) DEFERRABLE INITIALLY DEFERRED')
        c.execute('CREATE INDEX uj_dependent_from_created_idx ON main_unifiedjob_dependent_jobs (from_unifiedjob_id,from_unifiedjob_created)')
        c.execute('CREATE INDEX uj_dependent_to_created_idx ON main_unifiedjob_dependent_jobs (to_unifiedjob_id,to_unifiedjob_created)')


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as c:
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs DROP CONSTRAINT IF EXISTS unifiedjob_dependent_from_fk')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs DROP CONSTRAINT IF EXISTS unifiedjob_dependent_to_fk')
        c.execute('DROP INDEX IF EXISTS uj_dependent_from_created_idx')
        c.execute('DROP INDEX IF EXISTS uj_dependent_to_created_idx')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs DROP COLUMN from_unifiedjob_created')
        c.execute('ALTER TABLE main_unifiedjob_dependent_jobs DROP COLUMN to_unifiedjob_created')


class Migration(migrations.Migration):
    dependencies = [('main', '0217_joblaunchconfig_job_created_and_more')]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(forwards, backwards)],
            state_operations=[
                migrations.CreateModel(
                    name='UnifiedJobDependent',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('from_unifiedjob_created', models.DateTimeField(editable=False)),
                        ('to_unifiedjob_created', models.DateTimeField(editable=False)),
                        ('from_unifiedjob', models.ForeignKey(db_column='from_unifiedjob_id', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='main.unifiedjob')),
                        ('to_unifiedjob', models.ForeignKey(db_column='to_unifiedjob_id', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='main.unifiedjob')),
                    ], options={'db_table': 'main_unifiedjob_dependent_jobs'},
                ),
                migrations.AlterField(model_name='unifiedjob', name='dependent_jobs', field=models.ManyToManyField(editable=False, related_name='%(class)s_blocked_jobs', through='main.UnifiedJobDependent', to='main.unifiedjob')),
                migrations.AddIndex(model_name='unifiedjobdependent', index=models.Index(fields=['from_unifiedjob','from_unifiedjob_created'], name='uj_dependent_from_created_idx')),
                migrations.AddIndex(model_name='unifiedjobdependent', index=models.Index(fields=['to_unifiedjob','to_unifiedjob_created'], name='uj_dependent_to_created_idx')),
                migrations.AddConstraint(model_name='unifiedjobdependent', constraint=models.UniqueConstraint(fields=('from_unifiedjob','to_unifiedjob'), name='unifiedjob_dependent_unique')),
            ],
        )
    ]
