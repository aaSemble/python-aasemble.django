# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def copy_github_urls(apps, schema_editor):
    for ps in apps.get_model('buildsvc', 'PackageSource').objects.all():
        ps.git_url = 'https://github.com/%s/%s' % (ps.github_repository.repo_owner, ps.github_repository.repo_name) 
        ps.save()


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0006_packagesource_git_url'),
    ]

    operations = [
        migrations.RunPython(copy_github_urls, migrations.RunPython.noop),
    ]
