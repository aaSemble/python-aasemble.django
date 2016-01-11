# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.conf import settings
from django.db import migrations


def migrate_mirrors(apps, schema_editor):
    Mirror = apps.get_model("mirrorsvc", "Mirror")
    for mirror in Mirror.objects.all():
        id_based_dir = os.path.join(settings.MIRRORSVC_BASE_PATH, 'mirrors', str(mirror.id))
        uuid_based_dir = os.path.join(settings.MIRRORSVC_BASE_PATH, 'mirrors', str(mirror.uuid))
        if os.path.islink(id_based_dir) and os.path.isdir(uuid_based_dir):
            os.unlink(id_based_dir)
            os.symlink(str(mirror.uuid), id_based_dir)


def migrate_snapshots(apps, schema_editor):
    Snapshot = apps.get_model("mirrorsvc", "Snapshot")
    for snapshot in Snapshot.objects.all():
        id_based_dir = os.path.join(settings.MIRRORSVC_BASE_PATH, 'snapshots', str(snapshot.id))
        uuid_based_dir = os.path.join(settings.MIRRORSVC_BASE_PATH, 'snapshots', str(snapshot.uuid))
        if os.path.islink(id_based_dir) and os.path.isdir(uuid_based_dir):
            os.unlink(id_based_dir)
            os.symlink(str(snapshot.uuid), id_based_dir)


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0017_migrate_mirrors_to_uuid'),
    ]

    operations = [
        migrations.RunPython(migrate_mirrors),
        migrations.RunPython(migrate_snapshots),
    ]
