# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        ('mirrorsvc', '0008_mirror_extra_admins'),
    ]

    operations = [
        migrations.AddField(
            model_name='mirrorset',
            name='extra_admins',
            field=models.ManyToManyField(to='auth.Group'),
        ),
    ]
