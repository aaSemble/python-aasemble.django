# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0010_packagesource_last_built_name'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='repository',
            unique_together=set([('user', 'name')]),
        ),
    ]
