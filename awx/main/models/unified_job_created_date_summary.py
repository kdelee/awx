from django.db import models


class UnifiedJobCreatedDateSummary(models.Model):
    """Internal per-day summary of UnifiedJob rows by UTC created date.

    This model is used only as an optimization for historical aggregates.
    It must never be used as the source of truth for row-level data or to
    bypass RBAC checks; if a query cannot be answered safely from the
    summary, the system must fall back to the underlying UnifiedJob table.
    """

    SCOPE_GLOBAL = 'global'
    SCOPE_JOB_TEMPLATE = 'job_template'
    SCOPE_PROJECT = 'project'
    SCOPE_INVENTORY_SOURCE = 'inventory_source'
    SCOPE_WORKFLOW_JOB_TEMPLATE = 'workflow_job_template'
    SCOPE_CHOICES = (
        (SCOPE_GLOBAL, 'Global'),
        (SCOPE_JOB_TEMPLATE, 'Job template'),
        (SCOPE_PROJECT, 'Project'),
        (SCOPE_INVENTORY_SOURCE, 'Inventory source'),
        (SCOPE_WORKFLOW_JOB_TEMPLATE, 'Workflow job template'),
    )

    partition_date = models.DateField()
    scope_type = models.CharField(max_length=32, choices=SCOPE_CHOICES)
    scope_id = models.PositiveBigIntegerField(null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    summarized = models.BooleanField(default=False)
    total = models.PositiveBigIntegerField(default=0)
    status_totals = models.JSONField(default=dict)
    meta = models.JSONField(default=dict)

    class Meta:
        db_table = 'main_unifiedjob_created_date_summary'
        constraints = [
            models.UniqueConstraint(fields=('partition_date', 'scope_type', 'scope_id'), name='main_uj_created_summary_scope'),
            models.CheckConstraint(
                condition=(models.Q(scope_type='global', scope_id__isnull=True) | ~models.Q(scope_type='global') & models.Q(scope_id__isnull=False)),
                name='main_uj_created_summary_scope_id',
            ),
        ]

    def __str__(self):
        return f"UnifiedJobCreatedDateSummary({self.partition_date}, {self.scope_type}:{self.scope_id}, summarized={self.summarized})"
