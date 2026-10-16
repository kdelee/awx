from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0212_create_metrics_utility_functions'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnifiedJobCreatedDateSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('partition_date', models.DateField()),
                ('content_type_id', models.PositiveIntegerField(blank=True, null=True)),
                ('object_id', models.PositiveBigIntegerField(blank=True, null=True)),
                ('generated_at', models.DateTimeField(blank=True, null=True)),
                ('summarized', models.BooleanField(default=False)),
                ('total', models.PositiveBigIntegerField(default=0)),
                ('status_totals', models.JSONField(default=dict)),
                ('meta', models.JSONField(default=dict)),
            ],
            options={
                'db_table': 'main_unifiedjob_created_date_summary',
            },
        ),
        migrations.AddConstraint(
            model_name='unifiedjobcreateddatesummary',
            constraint=models.UniqueConstraint(fields=('partition_date', 'content_type_id', 'object_id'), name='main_uj_created_summary_resource'),
        ),
        migrations.AddConstraint(
            model_name='unifiedjobcreateddatesummary',
            constraint=models.CheckConstraint(
                condition=(models.Q(content_type_id__isnull=True, object_id__isnull=True) | models.Q(content_type_id__isnull=False, object_id__isnull=False)),
                name='main_uj_created_summary_resource_pair',
            ),
        ),
    ]
