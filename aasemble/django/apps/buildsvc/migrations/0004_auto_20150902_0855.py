# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0003_auto_20150831_1931'),
    ]

    operations = [
        migrations.AddField(
            model_name='buildrecord',
            name='build_counter',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='buildrecord',
            name='build_started',
            field=models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='buildrecord',
            name='sha',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
    ]
