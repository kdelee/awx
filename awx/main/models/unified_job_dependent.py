from django.db import models


class UnifiedJobDependent(models.Model):
    from_unifiedjob = models.ForeignKey('UnifiedJob', on_delete=models.CASCADE, db_column='from_unifiedjob_id', related_name='+')
    to_unifiedjob = models.ForeignKey('UnifiedJob', on_delete=models.CASCADE, db_column='to_unifiedjob_id', related_name='+')
    from_unifiedjob_created = models.DateTimeField(editable=False)
    to_unifiedjob_created = models.DateTimeField(editable=False)

    class Meta:
        app_label = 'main'
        db_table = 'main_unifiedjob_dependent_jobs'
        constraints = [models.UniqueConstraint(fields=('from_unifiedjob', 'to_unifiedjob'), name='unifiedjob_dependent_unique')]
        indexes = [
            models.Index(fields=('from_unifiedjob', 'from_unifiedjob_created'), name='uj_dependent_from_created_idx'),
            models.Index(fields=('to_unifiedjob', 'to_unifiedjob_created'), name='uj_dependent_to_created_idx'),
        ]
