import hashlib
import os.path
import re
from collections import OrderedDict

import deb822

from debian.debian_support import version_compare

from django.db import models

from aasemble.django.apps.buildsvc.models.source_package import SourcePackage

VALID_FORMATS = ('1.0',
                 '3.0 (native)',
                 '3.0 (quilt)')

re_orig_tarball = re.compile("orig\.tar\.(?:gz|bz2|xz)$")
re_diff_tarball = re.compile("diff\.tar\.(?:gz|bz2|xz)$")
re_diff = re.compile("diff\.(?:gz|bz2|xz)$")
re_native_tarball = re.compile("\.tar\.(?:gz|bz2|xz)$")
re_dsc = re.compile("\.dsc$")


class SourcePackageValidationException(Exception):
    pass


def guess_ftype_from_filename(fname):
    if re_orig_tarball.search(fname):
        return SOURCE_PACKAGE_FILE_TYPE_ORIG_TARBALL
    elif re_diff_tarball.search(fname):
        return SOURCE_PACKAGE_FILE_TYPE_DIFF_TARBALL
    elif re_diff.search(fname):
        return SOURCE_PACKAGE_FILE_TYPE_DIFF
    elif re_native_tarball.search(fname):
        return SOURCE_PACKAGE_FILE_TYPE_NATIVE
    elif re_dsc.search(fname):
        return SOURCE_PACKAGE_FILE_TYPE_DSC
    raise SourcePackageValidationException('Could not determine file type of %s' % (fname,))


def ftype_count(files):
    ftypes = [ft[0] for ft in SOURCE_PACKAGE_FILE_TYPE_CHOICES]
    seen_types = [f.file_type for f in files]
    return [seen_types.count(ft) for ft in ftypes]


def validate_1_0(files):
    fc = ftype_count(files)
    if fc in ([1, 0, 1, 0, 1],
              [0, 0, 0, 1, 1]):
        return True
    return False


def validate_3_0_native(files):
    fc = ftype_count(files)
    if fc in ([0, 0, 0, 1, 1],):
        return True
    return False


def validate_3_0_quilt(files):
    fc = ftype_count(files)
    if fc in ([1, 1, 0, 0, 1],):
        return True
    return False


def validate_fileset(format, files):
    if format == '1.0':
        return validate_1_0(files)
    elif format == '3.0 (quilt)':
        return validate_3_0_quilt(files)
    elif format == '3.0 (native)':
        return validate_3_0_native(files)


def _extract_info_from_dsc(dsc_file):
    with open(dsc_file, 'r') as fp:
        return deb822.Deb822(fp.read())


known_fields = ('Binary',
                'Version',
                'Maintainer',
                'Standards-Version',
                'Build-Depends',
                'Build-Depends-Indep',
                'Build-Conflicts',
                'Build-Conflicts-Indep',
                'Architecture',
                'Homepage',
                'Format')


def _kwargs_from_control(control, repository, dsc_file, files):
    kwargs = {}
    lower_known_fields = [f.lower() for f in known_fields]
    for k in control:
        k_lower = k.lower()
        if k_lower == 'source':
            sp, _ = SourcePackage.objects.get_or_create(name=control[k], repository=repository)
            kwargs['source_package'] = sp
        elif k_lower == 'format':
            if control[k] not in VALID_FORMATS:
                raise SourcePackageValidationException('Unknown format')
            kwargs[k_lower] = control[k]
        elif k_lower in lower_known_fields:
            kwargs[k.lower().replace('-', '_')] = control[k]
        elif k_lower in ('checksums-sha1', 'checksums-sha256', 'files'):
            hashfunc = {'files': hashlib.md5,
                        'checksums-sha1': hashlib.sha1,
                        'checksums-sha256': hashlib.sha256}[k_lower]
            for checksum, size, fname in [l.strip().split() for l in control[k].split('\n') if l.strip()]:
                if '/' in fname:
                    raise SourcePackageValidationException('No slashes allowed in file names')

                fpath = os.path.join(os.path.dirname(dsc_file), fname)

                digest = hashfunc(open(fpath, 'rb').read()).hexdigest()

                if digest != checksum:
                    raise SourcePackageValidationException('Checksum validation failed. %s != %s (%s)' % (digest, checksum, fname))
                else:
                    if fpath not in files:
                        files[fpath] = {}

                    files[fpath][k_lower] = checksum
    return kwargs


class SourcePackageVersion(models.Model):
    source_package = models.ForeignKey(SourcePackage)
    binary = models.TextField()
    architecture = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    maintainer = models.CharField(max_length=200)
    standards_version = models.CharField(max_length=50)
    build_depends = models.TextField()
    build_depends_indep = models.TextField()
    build_conflicts = models.TextField()
    build_conflicts_indep = models.TextField()
    homepage = models.CharField(max_length=250)
    format = models.CharField(max_length=50)
    package_source = models.ForeignKey('PackageSource', null=True)

    def __str__(self):
        return '%s_%s' % (self.source_package, self.version)

    class Meta:
        unique_together = ('source_package', 'version')

    def format_for_sources(self):
        data = deb822.Deb822()
        data['Package'] = self.source_package.name

        for field in known_fields:
            value = getattr(self, field.lower().replace('-', '_'))
            if value:
                data[field] = str(value)

        data['Directory'] = self.source_package.directory

        all_spvf = self.sourcepackageversionfile_set.all()

        data['Files'] = ''.join(['\n %s %s %s' % (spvf.md5sum, spvf.size, spvf.filename) for spvf in all_spvf])
        data['Checksums-Sha1'] = ''.join(['\n %s %s %s' % (spvf.sha1sum, spvf.size, spvf.filename) for spvf in all_spvf])
        data['Checksums-Sha256'] = ''.join(['\n %s %s %s' % (spvf.sha256sum, spvf.size, spvf.filename) for spvf in all_spvf])
        return str(data)

    @classmethod
    def does_series_already_have_this_or_newer_version(cls, series, sp, version):
        current_spv = series.source_package_versions.filter(source_package=sp)
        if not current_spv:
            return False
        else:
            return version_compare(version, current_spv[0].version) >= 0

    @classmethod
    def import_file(cls, series, dsc_file, package_source=None):
        control = _extract_info_from_dsc(dsc_file)

        files = OrderedDict()
        files[dsc_file] = {}

        kwargs = _kwargs_from_control(control, series.repository, dsc_file, files)

        kwargs['package_source'] = package_source

        fileobjs = []

        for f in files:
            with open(f, 'rb') as fp:
                contents = fp.read()

            kwargs2 = {'filename': f.split('/')[-1],
                       'file_type': guess_ftype_from_filename(f),
                       'md5sum': hashlib.md5(contents).hexdigest(),
                       'sha1sum': hashlib.sha1(contents).hexdigest(),
                       'sha256sum': hashlib.sha256(contents).hexdigest(),
                       'size': len(contents)}
            spvf = SourcePackageVersionFile(**kwargs2)
            spvf.original_filename = f
            fileobjs += [spvf]

        validate_fileset(kwargs['format'], fileobjs)

        if cls.does_series_already_have_this_or_newer_version(series,
                                                              kwargs['source_package'],
                                                              kwargs['version']):
            return 'Newer version already exists in repository'

        sp = kwargs.pop('source_package')
        version = kwargs.pop('version')
        spv, created = cls.objects.get_or_create(source_package=sp, version=version, defaults=kwargs)
        if created:
            for k in kwargs:
                setattr(spv, k, kwargs[k])
            spv.save()

        for f in fileobjs:
            f.source_package_version = spv
            f.save()
            f.store(f.original_filename)

        series.source_package_versions.add(spv)
        return spv

from aasemble.django.apps.buildsvc.models.source_package_version_file import (SOURCE_PACKAGE_FILE_TYPE_CHOICES,
                                                                              SOURCE_PACKAGE_FILE_TYPE_DIFF,
                                                                              SOURCE_PACKAGE_FILE_TYPE_DIFF_TARBALL,
                                                                              SOURCE_PACKAGE_FILE_TYPE_DSC,
                                                                              SOURCE_PACKAGE_FILE_TYPE_NATIVE,
                                                                              SOURCE_PACKAGE_FILE_TYPE_ORIG_TARBALL,
                                                                              SourcePackageVersionFile)  # noqa
