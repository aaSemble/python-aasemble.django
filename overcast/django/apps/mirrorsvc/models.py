from django.contrib.auth import models as auth_models
from django.db import models

class MirrorSet(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(auth_models.User)

class Mirror(models.Model):
    url = models.URLField(max_length=200)
    pocket = models.CharField(max_length=100)
    components = models.CharField(max_length=100)

class Architecture(models.Model):
    name = models.CharField(max_length=50)
    apt_mirror_prefix = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name
