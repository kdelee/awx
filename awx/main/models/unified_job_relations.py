from django.db import models


class UnifiedJobRoutingManager(models.Manager):
    def bulk_create(self, objs, *args, **kwargs):
        ids = {obj.unified_job_id for obj in objs if obj.unified_job_id and obj.unified_job_created is None}
        created = dict(self.model._meta.get_field('unified_job').remote_field.model.objects.filter(pk__in=ids).values_list('pk', 'created'))
        for obj in objs:
            if obj.unified_job_created is None:
                obj.unified_job_created = created.get(obj.unified_job_id)
        return super().bulk_create(objs, *args, **kwargs)


class UnifiedJobNotification(models.Model):
    objects = UnifiedJobRoutingManager()
    unified_job = models.ForeignKey('UnifiedJob', on_delete=models.CASCADE, db_column='unifiedjob_id', related_name='+')
    notification = models.ForeignKey('Notification', on_delete=models.CASCADE, db_column='notification_id', related_name='+')
    unified_job_created = models.DateTimeField(editable=False)

    class Meta:
        app_label = 'main'; db_table = 'main_unifiedjob_notifications'
        constraints = [models.UniqueConstraint(fields=('unified_job', 'notification'), name='unifiedjob_notification_unique')]
        indexes = [models.Index(fields=('unified_job', 'unified_job_created'), name='uj_notification_created_idx')]


class UnifiedJobLabel(models.Model):
    objects = UnifiedJobRoutingManager()
    unified_job = models.ForeignKey('UnifiedJob', on_delete=models.CASCADE, db_column='unifiedjob_id', related_name='+')
    label = models.ForeignKey('Label', on_delete=models.CASCADE, db_column='label_id', related_name='+')
    unified_job_created = models.DateTimeField(editable=False)

    class Meta:
        app_label = 'main'; db_table = 'main_unifiedjob_labels'
        constraints = [models.UniqueConstraint(fields=('unified_job', 'label'), name='unifiedjob_label_unique')]
        indexes = [models.Index(fields=('unified_job', 'unified_job_created'), name='uj_label_created_idx')]


class UnifiedJobCredential(models.Model):
    objects = UnifiedJobRoutingManager()
    unified_job = models.ForeignKey('UnifiedJob', on_delete=models.CASCADE, db_column='unifiedjob_id', related_name='+')
    credential = models.ForeignKey('Credential', on_delete=models.CASCADE, db_column='credential_id', related_name='+')
    unified_job_created = models.DateTimeField(editable=False)

    class Meta:
        app_label = 'main'; db_table = 'main_unifiedjob_credentials'
        constraints = [models.UniqueConstraint(fields=('unified_job', 'credential'), name='unifiedjob_credential_unique')]
        indexes = [models.Index(fields=('unified_job', 'unified_job_created'), name='uj_credential_created_idx')]
