# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.conf import settings
from django.db import migrations, models


def forwards_migrate_snapshots(apps, schema_editor):
    # Using historical version of Snapshot model
    Snapshot = apps.get_model("mirrorsvc", "Snapshot")
    for snapshot in Snapshot.objects.all():
        # Rename old directory to new directory with uuid, create symlink for old snapshots
        src_dir = os.path.join(settings.MIRRORSVC_BASE_PATH, 'snapshots', str(snapshot.id))
        new_dir = os.path.join(settings.MIRRORSVC_BASE_PATH, 'snapshots', str(snapshot.uuid))
        if os.path.isdir(src_dir) and not os.path.isdir(new_dir):
            os.rename(src_dir, new_dir)
            os.symlink(new_dir, src_dir)


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0014_migrate_v1_snapshots'),
    ]

    operations = [
        migrations.AlterField(
            model_name='snapshot',
            name='visible_to_v1_api',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(forwards_migrate_snapshots),
    ]
