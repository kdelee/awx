"""Temporary local PostgreSQL seed utility for testing migration 0214."""
import datetime

from django.utils.timezone import make_aware
from awx.main.models import UnifiedJob

UnifiedJob.objects.create(name="old", status="successful", created=make_aware(datetime.datetime(2020, 1, 1)))
UnifiedJob.objects.create(name="new", status="successful", created=make_aware(datetime.datetime(2026, 10, 16)))
print(UnifiedJob.objects.count())
