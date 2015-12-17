# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0016_buildrecord_build_finished'),
    ]

    operations = [
        migrations.AddField(
            model_name='packagesource',
            name='disabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='packagesource',
            name='last_failure',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='packagesource',
            name='last_failure_time',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
