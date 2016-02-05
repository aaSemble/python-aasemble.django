import hashlib
import os.path

import deb822

from django.core.files.base import File
from django.db import models

from aasemble.django.apps.buildsvc import storage
from aasemble.django.apps.buildsvc.enums import (BINARY_PACKAGE_TYPE_DDEB,
                                                 BINARY_PACKAGE_TYPE_DEB,
                                                 BINARY_PACKAGE_TYPE_UDEB)
from aasemble.django.apps.buildsvc.models.architecture import Architecture
from aasemble.django.apps.buildsvc.models.binary_build import BinaryBuild
from aasemble.django.apps.buildsvc.models.binary_package import BinaryPackage
from aasemble.django.apps.buildsvc.models.binary_package_version_user_field import BinaryPackageVersionUserField
from aasemble.django.apps.buildsvc.models.source_package import SourcePackage
from aasemble.django.apps.buildsvc.models.source_package_version import SourcePackageVersion


def split_description(description):
    if description == '':
        return '', ''

    if '\n' not in description:
        return description, ''

    lines = description.split('\n')
    return lines[0], '\n'.join([l[1:] for l in lines[1:]])


def join_description(short_description, long_description):
    return short_description + (long_description and (''.join(['\n %s' % l for l in long_description.split('\n')])) or '').rstrip(' ')


def _extract_info_from_deb(path):
    from aasemble.utils import run_cmd
    out = run_cmd(['dpkg-deb', '-I', path, 'control'])
    return deb822.Deb822(out)


class BinaryPackageVersion(models.Model):
    BINARY_PACKAGE_TYPE_CHOICES = ((BINARY_PACKAGE_TYPE_DEB, 'Debian package (.deb)'),
                                   (BINARY_PACKAGE_TYPE_UDEB, 'Debian-installer package (.udeb)'),
                                   (BINARY_PACKAGE_TYPE_DDEB, 'Debug Debian package (.ddeb)'))
    binary_package = models.ForeignKey(BinaryPackage)
    short_description = models.CharField(max_length=255, null=False, default='')
    long_description = models.TextField(null=False, default="")
    binary_build = models.ForeignKey(BinaryBuild)
    package_type = models.SmallIntegerField(choices=BINARY_PACKAGE_TYPE_CHOICES, default=BINARY_PACKAGE_TYPE_DEB)

    # Well-known fields
    version = models.CharField(max_length=200, null=False)
    architecture = models.CharField(max_length=32)
    maintainer = models.TextField(null=True)
    installed_size = models.IntegerField(null=True)
    depends = models.TextField(null=True)
    recommends = models.TextField(null=True)
    suggests = models.TextField(null=True)
    conflicts = models.TextField(null=True)
    replaces = models.TextField(null=True)
    provides = models.TextField(null=True)
    pre_depends = models.TextField(null=True)
    enhances = models.TextField(null=True)
    breaks = models.TextField(null=True)
    priority = models.TextField(null=True)
    section = models.TextField(null=True)
    homepage = models.CharField(max_length=250)

    # "Fileinfo" fields
    size = models.IntegerField()
    md5sum = models.CharField(max_length=32)
    sha1 = models.CharField(max_length=40)
    sha256 = models.CharField(max_length=64)

    # Not used? wtf?
    location = models.CharField(max_length=250)

    # Fields that are part of the model.
    model_fields = ('Version',
                    'Architecture',
                    'Maintainer',
                    'Installed-Size',
                    'Depends',
                    'Recommends',
                    'Suggests',
                    'Conflicts',
                    'Replaces',
                    'Provides',
                    'Pre-Depends',
                    'Enhances',
                    'Breaks',
                    'Priority',
                    'Section',
                    'Homepage')

    # Fields that have to do with the file itself
    fileinfo_fields = ('Size',
                       'Filename',
                       'MD5sum',
                       'SHA1',
                       'SHA256')

    # Fields that are derived from other data and thus should
    # just be ignored if read from the package (otherwise they'd
    # wind up as user fields and get included twice).
    generated_fields = ('Package',
                        'Source',
                        'Filename')

    def __str__(self):
        return '%s_%s_%s' % (self.binary_package.name, self.version, self.binary_build.architecture)

    @property
    def filename(self):
        sp = self.binary_build.source_package_version.source_package
        return 'pool/main/%s/%s/%s_%s_%s.deb' % (sp.name[0], sp.name, self.binary_package.name, self.version, self.architecture)

    def format_for_packages(self):
        data = deb822.Deb822()

        data['Package'] = self.binary_package.name
        data['Source'] = self.binary_build.source_package_version.source_package.name

        for field in self.model_fields:
            value = getattr(self, field.lower().replace('-', '_'))
            if value:
                data[field] = str(value)

        data['Filename'] = self.filename

        for field in self.fileinfo_fields:
            data[field] = str(getattr(self, field.lower().replace('-', '_')))

        data['Description'] = join_description(self.short_description, self.long_description)
        for bpvuf in self.binarypackageversionuserfield_set.all():
            data[bpvuf.name] = bpvuf.value
        return str(data)

    def store(self, fpath):
        destpath = os.path.join(self.binary_build.source_package_version.source_package.repository.user.username,
                                self.binary_build.source_package_version.source_package.repository.name,
                                self.filename)
        storage_driver = storage.get_repository_storage_driver()
        with open(fpath, 'rb') as fp:
            storage_driver.save(destpath, File(fp))

    @classmethod
    def import_file(cls, series, path, source_package_version=None):
        control = _extract_info_from_deb(path)

        bb_info = {'source_package': None,
                   'version': None,
                   'architecture': None}

        model_fields_lowercase = [f.lower() for f in cls.model_fields]
        ignored_fields_lowercase = [f.lower() for f in (cls.fileinfo_fields + cls.generated_fields)]

        user_fields = []
        kwargs = {}
        for k in control:
            k_lower = k.lower()
            if k_lower == 'package':
                bp, _ = BinaryPackage.objects.get_or_create(name=control[k], repository=series.repository)
                kwargs['binary_package'] = bp
            elif k_lower == 'source':
                bb_info['source_package'], _ = SourcePackage.objects.get_or_create(name=control[k], repository=series.repository)
            elif k_lower == 'version':
                kwargs['version'] = control[k]
                bb_info['version'] = control[k]
            elif k_lower == 'architecture':
                bb_info['architecture'] = Architecture.objects.get(name=control[k])
                kwargs['architecture'] = control[k]
            elif k_lower in model_fields_lowercase:
                kwargs[k.lower().replace('-', '_')] = control[k]
            elif k_lower == 'description':
                kwargs['short_description'], kwargs['long_description'] = split_description(control[k])
            elif k_lower not in ignored_fields_lowercase:
                user_fields += [BinaryPackageVersionUserField(k, control[k])]

        if not bb_info['source_package']:
            bb_info['source_package'], _ = SourcePackage.objects.get_or_create(name=path.split('/')[-2], repository=series.repository)

        if all(bb_info.values()):
            if not source_package_version:
                spv, _ = SourcePackageVersion.objects.get_or_create(source_package=bb_info['source_package'], version=bb_info['version'])
            else:
                spv = source_package_version
            kwargs['binary_build'], _ = BinaryBuild.objects.get_or_create(source_package_version=spv, architecture=bb_info['architecture'])

        with open(path, 'rb') as fp:
            contents = fp.read()

        kwargs['md5sum'] = hashlib.md5(contents).hexdigest()
        kwargs['sha1'] = hashlib.sha1(contents).hexdigest()
        kwargs['sha256'] = hashlib.sha256(contents).hexdigest()
        kwargs['size'] = len(contents)

        self, _ = cls.objects.get_or_create(**kwargs)
        self.store(path)

        series.binary_package_versions.add(self)

        for user_field in user_fields:
            user_field.binary_package_version = self
            user_field.save()
