from django.db import models


class SourcePackage(models.Model):
    name = models.CharField(max_length=200)
    repository = models.ForeignKey('Repository')

    def __str__(self):
        return '%s' % (self.name,)

    @property
    def directory(self):
        return 'pool/main/%s/%s' % (self.name[0], self.name)

    class Meta:
        unique_together = (('name', 'repository'),)
