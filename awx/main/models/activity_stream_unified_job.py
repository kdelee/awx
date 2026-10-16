from django.db import models


class ActivityStreamUnifiedJob(models.Model):
    activity_stream = models.ForeignKey('ActivityStream', on_delete=models.CASCADE, db_column='activitystream_id')
    unified_job = models.ForeignKey('UnifiedJob', on_delete=models.CASCADE, db_column='unifiedjob_id')
    unified_job_created = models.DateTimeField(editable=False)

    class Meta:
        app_label = 'main'
        db_table = 'main_activitystream_unified_job'
        constraints = [
            models.UniqueConstraint(
                fields=('activity_stream', 'unified_job'),
                name='activitystream_unifiedjob_unique',
            )
        ]
        indexes = [models.Index(fields=('unified_job', 'unified_job_created'), name='activitystream_uj_created_idx')]
