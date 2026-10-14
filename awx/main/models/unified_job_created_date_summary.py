from django.db import models
from django.utils import timezone


class UnifiedJobCreatedDateSummary(models.Model):
    """Internal per-day summary of UnifiedJob rows by UTC created date.

    This model is used only as an optimization for historical aggregates.
    It must never be used as the source of truth for row-level data or to
    bypass RBAC checks; if a query cannot be answered safely from the
    summary, the system must fall back to the underlying UnifiedJob table.
    """

    partition_date = models.DateField(primary_key=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    summarized = models.BooleanField(default=False)

    # Flexible JSON fields for initial MVP. Keys/shape are documented in the
    # spike plan docs and are intentionally permissive so we can iterate.
    totals = models.JSONField(default=dict)
    template_totals = models.JSONField(default=dict)
    org_totals = models.JSONField(default=dict)
    meta = models.JSONField(default=dict)

    class Meta:
        db_table = 'main_unifiedjob_created_date_summary'

    def __str__(self):
        return f"UnifiedJobCreatedDateSummary({self.partition_date}, summarized={self.summarized})"
