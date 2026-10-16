import datetime

import pytest
from django.db import connection
from django.utils.timezone import make_aware

from awx.main.models import Inventory, JobTemplate, Organization, Project


@pytest.mark.django_db
def test_unifiedjob_partition_probe_routes_historical_and_current_rows():
    """The disposable probe parent routes rows to both epoch partitions."""
    if connection.vendor != 'postgresql':
        pytest.skip('partition probe requires PostgreSQL')
    organization = Organization.objects.create(name='partition-probe-org')
    project = Project.objects.create(name='partition-probe-project', organization=organization)
    inventory = Inventory.objects.create(name='partition-probe-inventory', organization=organization)
    template = JobTemplate.objects.create(
        name='partition-probe-template',
        project=project,
        inventory=inventory,
        organization=organization,
    )
    historical = template.create_unified_job()
    historical.created = make_aware(datetime.datetime(2020, 1, 1))
    historical.save(update_fields=['created'])
    current = template.create_unified_job()
    current.created = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    current.save(update_fields=['created'])

    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO main_unifiedjob_partition_probe SELECT * FROM main_unifiedjob WHERE id IN (%s, %s)',
            [historical.pk, current.pk],
        )
        cursor.execute(
            'SELECT tableoid::regclass::text, count(*) '
            'FROM main_unifiedjob_partition_probe WHERE id IN (%s, %s) '
            'GROUP BY tableoid ORDER BY tableoid::regclass::text',
            [historical.pk, current.pk],
        )
        routed = cursor.fetchall()
        cursor.execute(
            'SELECT count(*) FROM main_unifiedjob_partition_probe WHERE id IN (%s, %s)',
            [historical.pk, current.pk],
        )
        total = cursor.fetchone()[0]

    assert total == 2
    assert len(routed) == 2
    assert all(count == 1 for _, count in routed)
