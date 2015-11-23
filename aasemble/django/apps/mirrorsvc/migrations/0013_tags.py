# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mirrorsvc', '0012_remove_uuid_null'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tags',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tag', models.CharField(max_length=200)),
                ('snapshot', models.ForeignKey(related_name='tags', to='mirrorsvc.Snapshot')),
            ],
        ),
    ]
