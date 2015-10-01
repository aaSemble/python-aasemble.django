# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0003_auto_20150930_0751'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mirror',
            name='components',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='mirror',
            name='series',
            field=models.CharField(max_length=200),
        ),
    ]
