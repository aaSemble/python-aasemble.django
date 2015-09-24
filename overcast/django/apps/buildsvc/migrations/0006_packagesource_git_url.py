# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0005_auto_20150923_1015'),
    ]

    operations = [
        migrations.AddField(
            model_name='packagesource',
            name='git_url',
            field=models.URLField(default='https://github.com/foo/bar'),
            preserve_default=False,
        ),
    ]
