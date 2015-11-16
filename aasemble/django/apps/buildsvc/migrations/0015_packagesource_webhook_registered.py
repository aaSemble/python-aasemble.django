# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0014_remove_uuid_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='packagesource',
            name='webhook_registered',
            field=models.BooleanField(default=False),
        ),
    ]
