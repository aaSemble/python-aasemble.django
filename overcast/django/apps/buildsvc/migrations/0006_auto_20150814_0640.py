# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0005_auto_20150813_2150'),
    ]

    operations = [
        migrations.CreateModel(
            name='PackageSource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('branch', models.CharField(max_length=100)),
            ],
        ),
        migrations.RemoveField(
            model_name='githubrepository',
            name='repo_branch',
        ),
        migrations.AddField(
            model_name='packagesource',
            name='github_repository',
            field=models.ForeignKey(to='buildsvc.GithubRepository'),
        ),
    ]
