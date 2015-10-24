# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0009_externaldependency'),
    ]

    operations = [
        migrations.AddField(
            model_name='packagesource',
            name='last_built_name',
            field=models.CharField(null=True, blank=True, max_length=64),
        ),
    ]
