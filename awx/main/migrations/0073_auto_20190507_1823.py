# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-05-07 18:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0072_v350_deprecate_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='foobar',
            field=models.IntegerField(blank=True, default=42, help_text='The foobar setting'),
        ),
        migrations.AddField(
            model_name='projectupdate',
            name='foobar',
            field=models.IntegerField(blank=True, default=42, help_text='The foobar setting'),
        ),
    ]
