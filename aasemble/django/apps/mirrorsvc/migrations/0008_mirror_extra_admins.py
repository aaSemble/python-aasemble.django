# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        ('mirrorsvc', '0007_mirror_refresh_in_progress'),
    ]

    operations = [
        migrations.AddField(
            model_name='mirror',
            name='extra_admins',
            field=models.ManyToManyField(to='auth.Group'),
        ),
    ]
