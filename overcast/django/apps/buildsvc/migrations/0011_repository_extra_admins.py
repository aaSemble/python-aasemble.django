# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        ('buildsvc', '0010_auto_20150820_1151'),
    ]

    operations = [
        migrations.AddField(
            model_name='repository',
            name='extra_admins',
            field=models.ManyToManyField(to='auth.Group'),
        ),
    ]
