# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0008_remove_packagesource_github_repository'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalDependency',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField()),
                ('series', models.CharField(max_length=200)),
                ('components', models.CharField(max_length=200, null=True, blank=True)),
                ('key', models.TextField()),
                ('own_series', models.ForeignKey(to='buildsvc.Series')),
            ],
        ),
    ]
