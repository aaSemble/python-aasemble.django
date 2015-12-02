# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0013_tags'),
    ]

    operations = [
        migrations.AddField(
            model_name='snapshot',
            name='visible_to_v1_api',
            field=models.BooleanField(default=True),
        ),
    ]
