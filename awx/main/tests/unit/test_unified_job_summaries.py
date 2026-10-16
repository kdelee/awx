from datetime import date, datetime, timezone

from awx.main.signals import mark_unified_job_summary_dirty_on_delete
from awx.main.utils.unified_job_summaries import combine_summary_and_live_counts, summary_dates_ready, summary_ready_dates, summary_scope_is_disjoint, summarized_unified_job_count, summarized_unified_job_count_for_dates


def test_summary_dates_require_every_historical_day(mocker):
    rows = mocker.patch('awx.main.utils.unified_job_summaries.UnifiedJobCreatedDateSummary.objects.filter')
    rows.return_value.values_list.return_value = [(date(2026, 10, 1), True)]

    assert summary_dates_ready(date(2026, 10, 1), date(2026, 10, 3)) is False


def test_summary_readiness_is_per_date(mocker):
    rows = mocker.patch('awx.main.utils.unified_job_summaries.UnifiedJobCreatedDateSummary.objects.filter')
    rows.return_value.values_list.return_value = [
        (date(2026, 10, 9), True),
        (date(2026, 10, 11), True),
    ]

    assert summary_ready_dates(date(2026, 10, 9), date(2026, 10, 13)) == {
        date(2026, 10, 9), date(2026, 10, 11)
    }


def test_deleted_job_marks_historical_summary_dirty(mocker):
    update = mocker.patch('awx.main.signals.UnifiedJobCreatedDateSummary.objects.update_or_create')
    job = mocker.Mock(created=datetime(2026, 10, 9, tzinfo=timezone.utc))

    mark_unified_job_summary_dirty_on_delete(None, job)

    update.assert_called_once_with(
        partition_date=date(2026, 10, 9),
        content_type_id=None,
        object_id=None,
        defaults={'summarized': False},
    )


def test_summary_count_uses_only_ready_dates(mocker):
    aggregate = mocker.patch('awx.main.utils.unified_job_summaries.UnifiedJobCreatedDateSummary.objects.filter')
    aggregate.return_value.filter.return_value.aggregate.return_value = {'total': 80}

    assert summarized_unified_job_count_for_dates({date(2026, 10, 9), date(2026, 10, 11)}, [(17, [1234])]) == 80
    aggregate.assert_called_once()


def test_summary_scopes_with_same_content_type_can_be_summed():
    """Separate visible resources of one type cannot count the same execution."""
    assert summary_scope_is_disjoint([(17, [10]), (17, [11])]) is True


def test_summary_scopes_with_different_content_types_require_live_fallback():
    """UJT and organization scopes may describe the same execution; do not add them."""
    assert summary_scope_is_disjoint([(17, [10]), (23, [44])]) is False


def test_summary_scopes_with_overlapping_resources_require_live_fallback():
    """Repeated resource identity means scope aggregation could double-count rows."""
    assert summary_scope_is_disjoint([(17, [10]), (17, [10, 11])]) is False


def test_hybrid_count_adds_disjoint_summary_and_live_dates_once():
    # Finalized date rows are excluded from live queryset by date boundary.
    assert combine_summary_and_live_counts(80, 20) == 100


def test_hybrid_count_uses_live_count_when_summary_missing():
    assert combine_summary_and_live_counts(None, 20) == 20


def test_summarized_count_uses_only_visible_unified_job_templates(mocker):
    aggregate = mocker.patch('awx.main.utils.unified_job_summaries.UnifiedJobCreatedDateSummary.objects.filter')
    aggregate.return_value.aggregate.return_value = {'total': 7}
    visible_template_ids = [10]

    result = summarized_unified_job_count('2026-10-01', '2026-10-02', 17, visible_template_ids)

    assert result == 7
    aggregate.assert_called_once_with(
        partition_date__gte='2026-10-01',
        partition_date__lt='2026-10-02',
        content_type_id=17,
        object_id__in=[10],
        summarized=True,
    )


def test_summarized_count_returns_zero_for_no_visible_resources():
    assert summarized_unified_job_count('2026-10-01', '2026-10-02', 17, []) == 0
