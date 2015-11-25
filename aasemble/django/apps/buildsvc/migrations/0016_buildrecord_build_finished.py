# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0015_packagesource_webhook_registered'),
    ]

    operations = [
        migrations.AddField(
            model_name='buildrecord',
            name='build_finished',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
