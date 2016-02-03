from django.db import models


class BinaryPackageVersionUserField(models.Model):
    binary_package_version = models.ForeignKey('BinaryPackageVersion')
    name = models.CharField(max_length=100)
    value = models.TextField()

    class Meta:
        order_with_respect_to = 'binary_package_version'
