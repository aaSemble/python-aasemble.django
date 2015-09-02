from __future__ import absolute_import

import os.path

from debian.debian_support import version_compare

from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string

from ..utils import run_cmd, recursive_render
from ..models import BuildRecord

class PackageBuilder(object):
    def __init__(self, basedir, package_source, build_record):
        self.basedir = basedir
        self.build_dependencies = []
        self.runtime_dependencies = []
        self.package_source = package_source
        self.build_record = build_record

    @property
    def builddir(self):
        return os.path.join(self.basedir, 'build')

    def get_version(self):
        """Derive version from code, fallback to build_counter"""
        return self.build_record.build_counter

    def build(self):
        self.build_record.logger.debug('Using %s to build' % (type(self)))
        package_version = self.package_version

        self.build_record.version = package_version
        self.build_record.save()

        self.package_source.last_built_version = package_version
        self.package_source.save()

        self.build_record.logger.debug('Detecting Build dependencies')
        self.build_dependencies += self.detect_build_dependencies()
        self.build_record.logger.info('Build dependencies: %s' % (', '.join(self.build_dependencies)))

        self.build_record.logger.debug('Detecting run-time dependencies')
        self.runtime_dependencies += self.detect_runtime_dependencies()
        self.build_record.logger.info('Runtime dependencies: %s' % (', '.join(self.runtime_dependencies)))

        self.populate_debian_dir()

        self.add_changelog_entry()
        self.build_source_package()
        self.build_binary_packages()

    def build_binary_packages(self):
        dsc = filter(lambda s:s.endswith('.dsc'), os.listdir(self.basedir))[0]

        with open(self.build_record.buildlog(), 'a+') as fp:
            buildlog = run_cmd(['sbuild',
                                '-n',
                                '--extra-repository=%s' % (self.package_source.series.binary_source_list(force_trusted=True),),
                                '-d', 'trusty',
                                '-A', dsc],
                                cwd=self.basedir,
                                stdout=fp,
                                logger=self.build_record.logger)

    def detect_runtime_dependencies(self):
        return []

    def detect_build_dependencies(self):
        reqfile = os.path.join(self.builddir, '.extra_build_packages')
        if os.path.exists(reqfile):
            with open(reqfile, 'r') as fp:
                return filter(lambda s:s, fp.read().split('\n'))
        return []

    def build_source_package(self):
        run_cmd(['dpkg-buildpackage', '-S', '-nc', '-uc', '-us'],
                cwd=self.builddir, override_env=self.env, logger=self.build_record.logger)

    def populate_debian_dir(self):
        self.build_record.logger.debug('Populating debian dir')
        recursive_render(os.path.join(os.path.dirname(__file__), '../templates/buildsvc/debian'),
                         os.path.join(self.builddir, 'debian'),
                         {'pkgname': self.sanitized_package_name,
                          'builder': self}, logger=self.build_record.logger)

    @property
    def env(self):
        return {'DEBEMAIL': settings.BUILDSVC_DEBEMAIL,
                'DEBFULLNAME': settings.BUILDSVC_DEBFULLNAME}

    def add_changelog_entry(self):
        fmt = '%a, %d %b %Y %H:%M:%S %z'
        rendered = render_to_string('buildsvc/changelog.deb',
                                    {'pkgname': self.sanitized_package_name,
                                     'version': self.package_version,
                                     'distribution': self.package_source.series.name,
                                     'full_name': self.env['DEBFULLNAME'],
                                     'email': self.env['DEBEMAIL'],
                                     'timestamp': timezone.now().strftime(fmt)})

        self.build_record.logger.info('New changelog entry: %s' % (rendered,))
        changelog = os.path.join(self.builddir, 'debian', 'changelog')

        if os.path.exists(changelog):
            with open(changelog, 'r') as fp:
                current_changelog = fp.read()
        else:
            current_changelog = ''

        with open(changelog, 'w') as fp:
            fp.write(rendered)
            fp.write(current_changelog)
  
    @property
    def sanitized_package_name(self):
        return self.package_name.replace('_', '-')

    @property
    def package_name(self):
        return self.name

    @property
    def binary_pkg_name(self):
        return self.package_name

    @property
    def name(self):
        return self.package_source.name

    @property
    def package_version(self):
        native_version = self.native_version
        if native_version:
            version = '%s+%d' % (native_version, self.build_record.build_counter)
        else:
            version = '%d' % (self.build_record.build_counter,)

        epoch = 0

        last_built_version = self.package_source.last_built_version
        if last_built_version:
            if ':' in last_built_version:
                epoch, cmp_ver = last_built_version.split(':', 1)
                epoch = int(epoch)
            else:
                cmp_ver = last_built_version

            if version_compare(version, cmp_ver) < 0:
                epoch = epoch+1
        
        if epoch:
            version = '%s:%s' % (epoch, version)

        return version

    @property
    def native_version(self):
        return None

    @classmethod
    def is_suitable(cls, path):
        return False

class PackageBuilderRegistry(object):
    builders = []

    @classmethod
    def register_builder(cls, builder):
        cls.builders.append(builder)


def choose_builder(path):
    print PackageBuilderRegistry.builders
    for builder in PackageBuilderRegistry.builders:
        if builder.is_suitable(path):
            return builder

from . import debian
from . import python
from . import golang
from . import generic
