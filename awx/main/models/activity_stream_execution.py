from django.db import models


class ActivityStreamExecutionThrough(models.Model):
    activity_stream = models.ForeignKey('ActivityStream', on_delete=models.CASCADE, db_column='activitystream_id')
    unified_job_created = models.DateTimeField(null=True, editable=False, db_column='unifiedjob_created')

    class Meta:
        abstract = True


class ActivityStreamJob(ActivityStreamExecutionThrough):
    job = models.ForeignKey('Job', on_delete=models.CASCADE, db_column='job_id')
    class Meta:
        db_table = 'main_activitystream_job'
        app_label = 'main'


class ActivityStreamProjectUpdate(ActivityStreamExecutionThrough):
    project_update = models.ForeignKey('ProjectUpdate', on_delete=models.CASCADE, db_column='projectupdate_id')
    class Meta:
        db_table = 'main_activitystream_project_update'
        app_label = 'main'


class ActivityStreamInventoryUpdate(ActivityStreamExecutionThrough):
    inventory_update = models.ForeignKey('InventoryUpdate', on_delete=models.CASCADE, db_column='inventoryupdate_id')
    class Meta:
        db_table = 'main_activitystream_inventory_update'
        app_label = 'main'


class ActivityStreamWorkflowJob(ActivityStreamExecutionThrough):
    workflow_job = models.ForeignKey('WorkflowJob', on_delete=models.CASCADE, db_column='workflowjob_id')
    class Meta:
        db_table = 'main_activitystream_workflow_job'
        app_label = 'main'


class ActivityStreamWorkflowApproval(ActivityStreamExecutionThrough):
    workflow_approval = models.ForeignKey('WorkflowApproval', on_delete=models.CASCADE, db_column='workflowapproval_id')
    class Meta:
        db_table = 'main_activitystream_workflow_approval'
        app_label = 'main'


class ActivityStreamAdHocCommand(ActivityStreamExecutionThrough):
    ad_hoc_command = models.ForeignKey('AdHocCommand', on_delete=models.CASCADE, db_column='adhoccommand_id')
    class Meta:
        db_table = 'main_activitystream_ad_hoc_command'
        app_label = 'main'
