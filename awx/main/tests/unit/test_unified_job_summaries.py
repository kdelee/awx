from awx.main.utils.unified_job_summaries import summarized_unified_job_count


def test_summarized_count_uses_scoped_finalized_rows(mocker):
    aggregate = mocker.patch('awx.main.utils.unified_job_summaries.UnifiedJobCreatedDateSummary.objects.filter')
    aggregate.return_value.aggregate.return_value = {'total': 42}

    result = summarized_unified_job_count('2026-10-01', '2026-10-02', 17, [10, 11])

    assert result == 42
    aggregate.assert_called_once_with(
        partition_date__gte='2026-10-01',
        partition_date__lt='2026-10-02',
        content_type_id=17,
        object_id__in=[10, 11],
        summarized=True,
    )


def test_summarized_count_returns_zero_for_no_visible_resources():
    assert summarized_unified_job_count('2026-10-01', '2026-10-02', 17, []) == 0
