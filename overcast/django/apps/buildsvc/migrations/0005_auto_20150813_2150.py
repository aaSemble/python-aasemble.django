# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('buildsvc', '0004_series'),
    ]

    operations = [
        migrations.RenameModel('Source', 'GithubRepository')
    ]
