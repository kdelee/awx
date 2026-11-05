"""Temporary local PostgreSQL seed utility; not part of the product code."""
import datetime
import uuid

from django.utils.timezone import make_aware
from awx.main.models import Job, SystemJob

suffix = uuid.uuid4().hex[:8]
rows = [
    (SystemJob.objects.create(name=f"seed-system-{suffix}"), datetime.datetime(2020, 1, 4)),
    (Job.objects.create(name=f"seed-orphan-{suffix}", status="successful"), datetime.datetime(2026, 10, 17)),
]

for execution, created in rows:
    execution.created = make_aware(created)
    execution.save(update_fields=["created"])

print([(type(execution).__name__, execution.pk, execution.created, execution.job_created) for execution, _ in rows])
