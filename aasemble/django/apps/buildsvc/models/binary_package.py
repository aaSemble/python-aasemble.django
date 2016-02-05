from django.db import models


class BinaryPackage(models.Model):
    name = models.CharField(max_length=200)
    repository = models.ForeignKey('Repository')

    def __str__(self):
        return '%s' % (self.name,)

    class Meta:
        unique_together = (('name', 'repository'),)
