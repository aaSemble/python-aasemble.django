# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0007_auto_20150923_1224'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='packagesource',
            name='github_repository',
        ),
    ]
