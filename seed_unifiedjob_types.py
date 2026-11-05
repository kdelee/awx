"""Temporary local PostgreSQL seed utility; not part of the product code."""
import datetime
import uuid

from django.utils.timezone import make_aware
from awx.main.models import (
    AdHocCommand,
    Inventory,
    InventorySource,
    InventoryUpdate,
    JobTemplate,
    Organization,
    Project,
    ProjectUpdate,
)

suffix = uuid.uuid4().hex[:8]
organization = Organization.objects.create(name=f"seed-org-{suffix}")
project = Project.objects.create(name=f"seed-project-{suffix}", organization=organization)
inventory = Inventory.objects.create(name=f"seed-inventory-{suffix}", organization=organization)
job_template = JobTemplate.objects.create(
    name=f"seed-jt-{suffix}", project=project, inventory=inventory, organization=organization
)
source = InventorySource.objects.create(name=f"seed-source-{suffix}", inventory=inventory, source="ec2")

rows = [
    (job_template.create_unified_job(), datetime.datetime(2020, 1, 1)),
    (job_template.create_unified_job(), datetime.datetime(2026, 10, 16)),
    (ProjectUpdate.objects.create(project=project, name=f"seed-pu-{suffix}"), datetime.datetime(2020, 1, 2)),
    (InventoryUpdate.objects.create(inventory_source=source, source="ec2"), datetime.datetime(2026, 10, 15)),
    (AdHocCommand.objects.create(name=f"seed-adhoc-{suffix}", inventory=inventory), datetime.datetime(2020, 1, 3)),
]

for execution, created in rows:
    execution.created = make_aware(created)
    execution.save(update_fields=["created"])

print([(type(execution).__name__, execution.pk, execution.created, execution.job_created) for execution, _ in rows])
