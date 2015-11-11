# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0006_snapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='mirror',
            name='refresh_in_progress',
            field=models.BooleanField(default=False),
        ),
    ]
