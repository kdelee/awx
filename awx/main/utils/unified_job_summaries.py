from django.db.models import Sum

from awx.main.models import UnifiedJobCreatedDateSummary


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
