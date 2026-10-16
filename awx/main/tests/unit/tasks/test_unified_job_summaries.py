import datetime
from contextlib import nullcontext
from unittest.mock import MagicMock

from awx.main.tasks import unified_job_summaries as summaries


def test_date_bounds_are_utc_half_open():
    start, end = summaries._date_bounds(datetime.date(2026, 10, 15))

    assert start == datetime.datetime(2026, 10, 15, tzinfo=datetime.timezone.utc)
    assert end == datetime.datetime(2026, 10, 16, tzinfo=datetime.timezone.utc)


def test_summary_task_skips_date_with_running_job(mocker):
    jobs = MagicMock()
    jobs.exclude.return_value.exists.return_value = True
    mocker.patch.object(summaries, '_date_queryset', return_value=jobs)
    mocker.patch.object(summaries, 'advisory_lock', return_value=nullcontext(True))
    summaries_table = mocker.patch.object(summaries.UnifiedJobCreatedDateSummary.objects, 'filter')

    result = summaries.generate_unified_job_created_date_summary(datetime.date(2026, 10, 15))

    assert result is False
    summaries_table.assert_called_once_with(
        partition_date=datetime.date(2026, 10, 15), content_type_id=None, object_id=None
    )
    summaries_table.return_value.update.assert_called_once_with(summarized=False)


def test_summary_task_does_not_run_when_date_lock_is_held(mocker):
    mocker.patch.object(summaries, '_date_queryset')
    mocker.patch.object(summaries, 'advisory_lock', return_value=nullcontext(False))

    result = summaries.generate_unified_job_created_date_summary('2026-10-15')

    assert result is False
    summaries._date_queryset.assert_not_called()


def test_hourly_retry_queues_only_recent_dates(mocker):
    current = datetime.datetime(2026, 10, 16, 1, tzinfo=datetime.timezone.utc)
    mocker.patch.object(summaries, 'now', return_value=current)
    enqueue = mocker.patch.object(summaries, 'enqueue_unified_job_created_date_summary')

    summaries.retry_unified_job_created_date_summaries()

    assert [call.args[0] for call in enqueue.call_args_list] == [
        datetime.date(2026, 10, 15),
        datetime.date(2026, 10, 14),
    ]
