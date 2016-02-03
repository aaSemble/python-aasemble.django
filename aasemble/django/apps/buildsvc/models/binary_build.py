from django.db import models


class BinaryBuild(models.Model):
    source_package_version = models.ForeignKey('SourcePackageVersion')
    architecture = models.ForeignKey('Architecture')

    def __str__(self):
        return '%s_%s' % (self.source_package_version, self.architecture)
