from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Feature(models.Model):
    name = models.CharField(max_length=50, unique=True)
    on_by_default = models.BooleanField(default=False)
    description = models.TextField()
    users = models.ManyToManyField(User, related_name='features')

    def __str__(self):
        return self.name
