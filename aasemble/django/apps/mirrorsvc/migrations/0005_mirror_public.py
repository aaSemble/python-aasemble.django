# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0004_auto_20150930_0752'),
    ]

    operations = [
        migrations.AddField(
            model_name='mirror',
            name='public',
            field=models.BooleanField(default=False),
        ),
    ]
