# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0002_auto_20150827_1245'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='githubrepository',
            unique_together=set([('user', 'repo_owner', 'repo_name')]),
        ),
    ]
