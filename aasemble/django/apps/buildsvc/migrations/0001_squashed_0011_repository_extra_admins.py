# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='GithubRepository',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('repo_owner', models.CharField(max_length=100)),
                ('repo_name', models.CharField(max_length=100)),
                ('last_seen_revision', models.CharField(max_length=64, null=True, blank=True)),
                ('build_counter', models.IntegerField(default=0)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('builds_enabled', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('key_id', models.CharField(max_length=100)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Series',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('repository', models.ForeignKey(to='buildsvc.Repository')),
            ],
        ),
        migrations.CreateModel(
            name='PackageSource',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('branch', models.CharField(max_length=100)),
                ('github_repository', models.ForeignKey(to='buildsvc.GithubRepository')),
                ('series', models.ForeignKey(default=1, to='buildsvc.Series')),
                ('build_counter', models.IntegerField(default=0)),
                ('last_seen_revision', models.CharField(max_length=64, null=True, blank=True)),
            ],
        ),
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
        migrations.CreateModel(
            name='BuildRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version', models.CharField(max_length=50)),
                ('source', models.ForeignKey(to='buildsvc.PackageSource')),
            ],
        ),
        migrations.AlterModelOptions(
            name='githubrepository',
            options={'ordering': ['repo_owner', 'repo_name'], 'verbose_name_plural': 'Github repositories'},
        ),
        migrations.AddField(
            model_name='repository',
            name='extra_admins',
            field=models.ManyToManyField(to='auth.Group'),
        ),
    ]
