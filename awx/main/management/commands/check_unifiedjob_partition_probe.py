from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Validate the PostgreSQL UnifiedJob partition probe structure.'

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('UnifiedJob partition probe requires PostgreSQL')

        with connection.cursor() as cursor:
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

        self.stdout.write(self.style.SUCCESS(f'UnifiedJob partition probe is valid ({total} rows)'))
