# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0001_squashed_0011_repository_extra_admins'),
    ]

    operations = [
        migrations.AddField(
            model_name='packagesource',
            name='last_built_version',
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='packagesource',
            name='series',
            field=models.ForeignKey(to='buildsvc.Series'),
        ),
    ]
