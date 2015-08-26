# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0009_buildrecord'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='githubrepository',
            options={'ordering': ['repo_owner', 'repo_name'], 'verbose_name_plural': 'Github repositories'},
        ),
    ]
