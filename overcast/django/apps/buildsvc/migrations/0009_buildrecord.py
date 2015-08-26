# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildsvc', '0008_auto_20150814_0719'),
    ]

    operations = [
        migrations.CreateModel(
            name='BuildRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version', models.CharField(max_length=50)),
                ('source', models.ForeignKey(to='buildsvc.PackageSource')),
            ],
        ),
    ]
