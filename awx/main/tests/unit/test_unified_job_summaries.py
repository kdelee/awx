from awx.main.utils.unified_job_summaries import combine_summary_and_live_counts, summarized_unified_job_count


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
