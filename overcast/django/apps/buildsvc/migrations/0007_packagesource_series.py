# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0006_auto_20150814_0640'),
    ]

    operations = [
        migrations.AddField(
            model_name='packagesource',
            name='series',
            field=models.ForeignKey(default=1, to='buildsvc.Series'),
            preserve_default=False,
        ),
    ]
