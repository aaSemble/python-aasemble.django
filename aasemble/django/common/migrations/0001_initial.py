# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


def add_initial_features(apps, schema_editor):
    Feature = apps.get_model("common", "Feature")
    Feature.objects.create(name='DUMMY_FEATURE_EVERYONE_HAS_BY_DEFAULT',
                           on_by_default=True, description='Dummy feature. On by default.')
    Feature.objects.create(name='DUMMY_FEATURE_NOONE_HAS_BY_DEFAULT',
                           on_by_default=False, description='Dummy feature. Off by default.')


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Feature',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('on_by_default', models.BooleanField(default=False)),
                ('description', models.TextField()),
                ('users', models.ManyToManyField(related_name='features', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(add_initial_features)
    ]
