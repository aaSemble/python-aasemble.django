import json
import uuid

from django.contrib.auth import models as auth_models
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Cluster(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(auth_models.User, null=True)
    json = models.BinaryField(null=True, blank=True)

    def __str__(self):
        return str(self.uuid)

    def clean_fields(self):
        try:
            json.loads(self.json)
        except ValueError:
            raise ValidationError('JSON field not valid JSON')
        return super(Cluster, self).clean_fields()


@python_2_unicode_compatible
class Node(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    internal_ip = models.GenericIPAddressField(protocol='IPv4')
    cluster = models.ForeignKey(Cluster)

    def __str__(self):
        return '%s:%s' % (self.cluster, self.uuid)
