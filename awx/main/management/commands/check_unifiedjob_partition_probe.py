import datetime
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils.timezone import make_aware

from awx.main.models import Inventory, JobTemplate, Organization, Project


class Command(BaseCommand):
    help = 'Validate the PostgreSQL UnifiedJob partition probe structure.'

    def add_arguments(self, parser):
        parser.add_argument('--copy-existing', action='store_true', help='Copy current UnifiedJob rows into the probe before checking routing.')
        parser.add_argument('--seed', action='store_true', help='Create historical and current probe rows before checking routing.')

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('UnifiedJob partition probe requires PostgreSQL')

        if options['seed']:
            suffix = uuid.uuid4().hex[:8]
            organization = Organization.objects.create(name=f'partition-probe-org-{suffix}')
            project = Project.objects.create(name=f'partition-probe-project-{suffix}', organization=organization)
            inventory = Inventory.objects.create(name=f'partition-probe-inventory-{suffix}', organization=organization)
            template = JobTemplate.objects.create(
                name=f'partition-probe-template-{suffix}', project=project, inventory=inventory, organization=organization
            )
            historical = template.create_unified_job()
            historical.created = make_aware(datetime.datetime(2020, 1, 1))
            historical.save(update_fields=['created'])
            template.create_unified_job()
            options['copy_existing'] = True

        with connection.cursor() as cursor:
            if options['copy_existing']:
                cursor.execute('INSERT INTO main_unifiedjob_partition_probe SELECT * FROM main_unifiedjob ON CONFLICT DO NOTHING')

            cursor.execute(
                """
                SELECT c.relname
                FROM pg_inherits i
                JOIN pg_class c ON c.oid = i.inhrelid
                JOIN pg_class p ON p.oid = i.inhparent
                WHERE p.relname = 'main_unifiedjob_partition_probe'
                ORDER BY c.relname
                """
            )
            partitions = [row[0] for row in cursor.fetchall()]
            if partitions != [
                'main_unifiedjob_partition_probe_after_epoch',
                'main_unifiedjob_partition_probe_before_epoch',
            ]:
                raise CommandError(f'Unexpected probe partitions: {partitions}')

            cursor.execute(
                """
                SELECT count(*)
                FROM main_unifiedjob_partition_probe
                """
            )
            total = cursor.fetchone()[0]
            cursor.execute(
                "SELECT tableoid::regclass::text, count(*) FROM main_unifiedjob_partition_probe GROUP BY tableoid ORDER BY 1"
            )
            routed = cursor.fetchall()

        self.stdout.write(self.style.SUCCESS(f'UnifiedJob partition probe is valid ({total} rows)'))
        for table, count in routed:
            self.stdout.write(f'  {table}: {count}')
