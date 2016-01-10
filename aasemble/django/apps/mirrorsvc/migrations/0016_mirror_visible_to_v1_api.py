# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0015_change_visible_to_v1_column_to_false'),
    ]

    operations = [
        migrations.AddField(
            model_name='mirror',
            name='visible_to_v1_api',
            field=models.BooleanField(default=True),
        ),
    ]
