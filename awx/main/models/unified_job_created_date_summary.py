from django.db import models


class UnifiedJobCreatedDateSummary(models.Model):
    """Internal per-day summary of UnifiedJob rows by UTC created date.

    This model is used only as an optimization for historical aggregates.
    It must never be used as the source of truth for row-level data or to
    bypass RBAC checks; if a query cannot be answered safely from the
    summary, the system must fall back to the underlying UnifiedJob table.
    """

    id = models.BigAutoField(primary_key=True)
    partition_date = models.DateField()
    # Matches AWX RBAC terminology: content_type_id + object_id identify a
    # permission-bearing resource. Both are NULL for the global aggregate.
    content_type_id = models.PositiveIntegerField(null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    organization_id = models.PositiveBigIntegerField(null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    summarized = models.BooleanField(default=False)
    total = models.PositiveBigIntegerField(default=0)
    status_totals = models.JSONField(default=dict)
    meta = models.JSONField(default=dict)

    class Meta:
        db_table = 'main_unifiedjob_created_date_summary'
        indexes = [
            models.Index(fields=('partition_date', 'content_type_id', 'object_id'), name='uj_summary_date_resource'),
            models.Index(fields=('content_type_id', 'object_id', 'partition_date'), name='uj_summary_resource_date'),
        ]
        constraints = [
            models.UniqueConstraint(fields=('partition_date', 'content_type_id', 'object_id'), name='main_uj_created_summary_resource'),
            models.CheckConstraint(
                condition=(models.Q(content_type_id__isnull=True, object_id__isnull=True) | models.Q(content_type_id__isnull=False, object_id__isnull=False)),
                name='main_uj_created_summary_resource_pair',
            ),
        ]

    def __str__(self):
        return f"UnifiedJobCreatedDateSummary({self.partition_date}, {self.content_type_id}:{self.object_id}, summarized={self.summarized})"
