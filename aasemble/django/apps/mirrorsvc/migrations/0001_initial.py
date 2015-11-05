# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


def add_initial_architectures(apps, schema_editor):
    Architecture = apps.get_model('mirrorsvc', 'Architecture')
    Architecture.objects.create(name='x86', apt_mirror_prefix='i386')
    Architecture.objects.create(name='x86 64-bit', apt_mirror_prefix='amd64')
    Architecture.objects.create(name='Source', apt_mirror_prefix='src')


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Architecture',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('apt_mirror_prefix', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='Mirror',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField()),
                ('pocket', models.CharField(max_length=100)),
                ('components', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='MirrorSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(
            code=add_initial_architectures,
        ),
    ]
