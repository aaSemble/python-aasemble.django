# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0004_auto_20150902_0855'),
    ]

    operations = [
        migrations.AlterField(
            model_name='packagesource',
            name='series',
            field=models.ForeignKey(related_name='sources', to='buildsvc.Series'),
        ),
        migrations.AlterField(
            model_name='series',
            name='repository',
            field=models.ForeignKey(related_name='series', to='buildsvc.Repository'),
        ),
    ]
