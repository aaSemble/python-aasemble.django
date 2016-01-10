# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.conf import settings
from django.db import migrations, models


def forwards_migrate_mirrors(apps, schema_editor):
    # Using historical version of Mirror model
    Mirror = apps.get_model("mirrorsvc", "Mirror")
    for mirror in Mirror.objects.all():
        # Rename old directory to new directory with uuid, create symlink for old mirrors
        src_dir = os.path.join(settings.MIRRORSVC_BASE_PATH, 'mirrors', str(mirror.id))
        new_dir = os.path.join(settings.MIRRORSVC_BASE_PATH, 'mirrors', str(mirror.uuid))
        if os.path.isdir(src_dir) and not os.path.isdir(new_dir):
            os.rename(src_dir, new_dir)
            os.symlink(new_dir, src_dir)


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0016_mirror_visible_to_v1_api'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mirror',
            name='visible_to_v1_api',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(forwards_migrate_mirrors),
    ]
