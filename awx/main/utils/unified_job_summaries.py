from django.db.models import Q, Sum

import logging
from datetime import timedelta

from awx.main.models import UnifiedJobCreatedDateSummary

logger = logging.getLogger(__name__)


def combine_summary_and_live_counts(summarized_count, live_count):
    """Combine disjoint finalized-date and live-date counts."""
    if summarized_count is None:
        return live_count
    return summarized_count + live_count


def summary_scope_is_disjoint(scope_groups):
    """Return whether scope groups partition executions without double-counting.

    Different ContentTypes can point at the same execution through different
    permission paths, so mixed resource scopes require live-query fallback.
    """
    content_types = {content_type_id for content_type_id, _ in scope_groups}
    if len(content_types) > 1:
        return False

    seen = set()
    for content_type_id, object_ids in scope_groups:
        resources = {(content_type_id, object_id) for object_id in object_ids}
        if seen & resources:
            return False
        seen.update(resources)
    return True


def summary_ready_dates(start_date, end_date):
    """Return finalized dates individually; unfinished dates remain live-counted."""
    rows = UnifiedJobCreatedDateSummary.objects.filter(
        partition_date__gte=start_date,
        partition_date__lt=end_date,
        content_type_id__isnull=True,
        object_id__isnull=True,
    ).values_list('partition_date', 'summarized')
    ready = {date for date, summarized in rows if summarized}
    expected = {start_date + timedelta(days=offset) for offset in range((end_date - start_date).days)}
    incomplete = expected - ready
    if incomplete:
        logger.warning('UnifiedJob summaries incomplete for dates %s; using live counts for those dates', sorted(incomplete))
    return ready


def summary_dates_ready(start_date, end_date):
    """Compatibility predicate: true only when every date is finalized."""
    expected = (end_date - start_date).days
    return len(summary_ready_dates(start_date, end_date)) == expected


def summarized_unified_job_count_for_dates(ready_dates, scope_groups):
    """Sum finalized rows only for ready dates and disjoint visible scopes."""
    if not ready_dates or not summary_scope_is_disjoint(scope_groups):
        return None
    scope_filter = Q()
    for content_type_id, object_ids in scope_groups:
        if object_ids:
            scope_filter |= Q(content_type_id=content_type_id, object_id__in=object_ids)
    if not scope_filter:
        return 0
    result = UnifiedJobCreatedDateSummary.objects.filter(
        partition_date__in=ready_dates,
        summarized=True,
    ).filter(scope_filter).aggregate(total=Sum('total'))
    return result['total'] if result['total'] is not None else None


def summarized_visible_scope_groups_count(ready_dates, scope_groups):
    """Count summary rows for mixed child scopes; each summary row is unique."""
    if not ready_dates or not scope_groups:
        return 0
    visibility = Q()
    for content_type_id, object_ids in scope_groups:
        if object_ids:
            visibility |= Q(content_type_id=content_type_id, object_id__in=object_ids)
    if not visibility:
        return 0
    result = UnifiedJobCreatedDateSummary.objects.filter(
        partition_date__in=ready_dates, summarized=True
    ).filter(visibility).aggregate(total=Sum('total'))
    return result['total'] or 0


def summarized_visible_scope_count(ready_dates, content_type_id, object_ids, organization_ids):
    """Count canonical resource summaries visible directly or by organization."""
    if not ready_dates:
        return 0
    visibility = Q(content_type_id=content_type_id, object_id__in=object_ids)
    if organization_ids:
        visibility |= Q(organization_id__in=organization_ids)
    result = UnifiedJobCreatedDateSummary.objects.filter(
        partition_date__in=ready_dates,
        summarized=True,
    ).filter(visibility).aggregate(total=Sum('total'))
    return result['total'] or 0


def summarized_unified_job_count(start, end, content_type_id, object_ids):
    """Return finalized summary count for visible RBAC resources.

    Returns None when no scoped summary rows exist, allowing callers to fall
    back to the live RBAC queryset. This helper never uses global summaries.
    """
    if not object_ids:
        return 0

    result = UnifiedJobCreatedDateSummary.objects.filter(
        partition_date__gte=start,
        partition_date__lt=end,
        content_type_id=content_type_id,
        object_id__in=object_ids,
        summarized=True,
    ).aggregate(total=Sum('total'))
    return result['total'] if result['total'] is not None else None
