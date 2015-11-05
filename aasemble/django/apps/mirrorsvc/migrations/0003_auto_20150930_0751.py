# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0002_auto_20150930_0701'),
    ]

    operations = [
        migrations.RenameField(
            model_name='mirror',
            old_name='pocket',
            new_name='series',
        ),
    ]
