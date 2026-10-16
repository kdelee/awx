import datetime
import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.timezone import now
from dispatcherd.publish import task

from ansible_base.lib.utils.db import advisory_lock
from awx.main.dispatch import get_task_queuename
from awx.main.models import (
    InventorySource,
    InventoryUpdate,
    Project,
    ProjectUpdate,
    UnifiedJob,
    UnifiedJobCreatedDateSummary,
    UnifiedJobTemplate,
    WorkflowJob,
    WorkflowJobTemplate,
)

logger = logging.getLogger('awx.main.tasks.unified_job_summaries')

TERMINAL_STATUSES = ('successful', 'failed', 'error', 'canceled')


def enqueue_unified_job_created_date_summary(created):
    """Queue summary work without doing database aggregation in a job hook."""
    partition_date = created.date() if hasattr(created, 'date') else created
    generate_unified_job_created_date_summary.delay(partition_date.isoformat())


def _date_bounds(partition_date):
    start = datetime.datetime.combine(partition_date, datetime.time.min, tzinfo=datetime.timezone.utc)
    return start, start + datetime.timedelta(days=1)


def _date_queryset(partition_date):
    start, end = _date_bounds(partition_date)
    return UnifiedJob.objects.filter(created__gte=start, created__lt=end)


@task(queue=get_task_queuename, timeout=3600, on_duplicate='queue_one')
def generate_unified_job_created_date_summary(partition_date):
    """Generate global and job-template summaries after jobs terminate.

    Other ownership scopes still require separate subtype-aware generation
    before non-admin views can consume summary counts.
    """
    if isinstance(partition_date, str):
        partition_date = datetime.date.fromisoformat(partition_date)

    lock_name = f'unified_job_created_date_summary_{partition_date.isoformat()}'
    with advisory_lock(lock_name, wait=False) as acquired:
        if not acquired:
            return False

        jobs = _date_queryset(partition_date)
        if jobs.exclude(status__in=TERMINAL_STATUSES).exists():
            UnifiedJobCreatedDateSummary.objects.filter(
                partition_date=partition_date,
                content_type_id=None,
                object_id=None,
            ).update(summarized=False)
            return False

        UnifiedJobCreatedDateSummary.objects.filter(partition_date=partition_date).delete()
        status_totals = dict(jobs.values('status').annotate(count=Count('id')).values_list('status', 'count'))
        UnifiedJobCreatedDateSummary.objects.update_or_create(
            partition_date=partition_date,
            content_type_id=None,
            object_id=None,
            defaults={
                'generated_at': now(),
                'summarized': True,
                'total': jobs.count(),
                'status_totals': status_totals,
            },
        )
        scoped = {}
        for row in jobs.values('unified_job_template_id', 'status').annotate(count=Count('id')):
            template_id = row['unified_job_template_id']
            if template_id is None:
                continue
            scoped.setdefault(template_id, {})[row['status']] = row['count']

        for template_id, counts in scoped.items():
            UnifiedJobCreatedDateSummary.objects.update_or_create(
                partition_date=partition_date,
                content_type_id=ContentType.objects.get_for_model(UnifiedJobTemplate).id,
                object_id=template_id,
                defaults={
                    'generated_at': now(),
                    'summarized': True,
                    'total': sum(counts.values()),
                    'status_totals': counts,
                },
            )

        scope_models = (
            (ProjectUpdate, Project, 'project_id'),
            (InventoryUpdate, InventorySource, 'inventory_source_id'),
            (WorkflowJob, WorkflowJobTemplate, 'workflow_job_template_id'),
        )
        start, end = _date_bounds(partition_date)
        scoped_count = len(scoped)
        for model, resource_model, scope_field in scope_models:
            content_type_id = ContentType.objects.get_for_model(resource_model).id
            rows = model.objects.filter(created__gte=start, created__lt=end).values(scope_field, 'status').annotate(count=Count('id'))
            grouped = {}
            for row in rows:
                if row[scope_field] is not None:
                    grouped.setdefault(row[scope_field], {})[row['status']] = row['count']
            for object_id, counts in grouped.items():
                UnifiedJobCreatedDateSummary.objects.update_or_create(
                    partition_date=partition_date,
                    content_type_id=content_type_id,
                    object_id=object_id,
                    defaults={
                        'generated_at': now(),
                        'summarized': True,
                        'total': sum(counts.values()),
                        'status_totals': counts,
                    },
                )
                scoped_count += 1

        logger.info('Generated global and %d scoped summaries for %s', scoped_count, partition_date)
        return True
