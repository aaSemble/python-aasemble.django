# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mirrorsvc', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mirror',
            name='owner',
            field=models.ForeignKey(default=1, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='mirrorset',
            name='mirrors',
            field=models.ManyToManyField(to='mirrorsvc.Mirror'),
        ),
    ]
