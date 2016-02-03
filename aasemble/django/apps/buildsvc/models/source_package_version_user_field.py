from django.db import models


class SourcePackageVersionUserField(models.Model):
    source_package_version = models.ForeignKey('SourcePackageVersion')
    name = models.CharField(max_length=100)
    value = models.TextField()

    class Meta:
        order_with_respect_to = 'source_package_version'
