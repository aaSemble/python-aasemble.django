# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0007_packagesource_series'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='githubrepository',
            options={'verbose_name_plural': 'Github repositories'},
        ),
        migrations.AlterModelOptions(
            name='repository',
            options={'verbose_name_plural': 'repositories'},
        ),
        migrations.AlterModelOptions(
            name='series',
            options={'verbose_name_plural': 'series'},
        ),
        migrations.RemoveField(
            model_name='githubrepository',
            name='build_counter',
        ),
        migrations.RemoveField(
            model_name='githubrepository',
            name='builds_enabled',
        ),
        migrations.RemoveField(
            model_name='githubrepository',
            name='last_seen_revision',
        ),
        migrations.AddField(
            model_name='packagesource',
            name='build_counter',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='packagesource',
            name='last_seen_revision',
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
    ]
