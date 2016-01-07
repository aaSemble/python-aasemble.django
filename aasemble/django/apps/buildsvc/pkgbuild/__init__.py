from __future__ import absolute_import

import os
import sys

import dbuild

from debian.debian_support import version_compare

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

import yaml

from ....utils import recursive_render


class BuilderBackend(object):
    pass


class DbuildBuilderBackend(BuilderBackend):
    def source_build(self, basedir, sourcedir):
        dbuild.docker_build(build_dir=basedir,
                            build_type='source',
                            source_dir=sourcedir,
                            build_owner=os.getuid(),
                            proxy=getattr(settings, 'AASEMBLE_BUILDSVC_BUILDER_HTTP_PROXY', ))

    def binary_build(self, basedir, parallel=1):
        dbuild.docker_build(build_dir=basedir,
                            build_type='binary',
                            build_owner=os.getuid(),
                            parallel=parallel,
                            proxy=getattr(settings, 'AASEMBLE_BUILDSVC_BUILDER_HTTP_PROXY', ))


def get_build_backend(settings=settings):
    backend_name = getattr(settings, 'AASEMBLE_BUILDSVC_BUILD_BACKEND', 'dbuild')
    if backend_name == 'dbuild':
        return DbuildBuilderBackend()


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
        self.package_source.last_built_name = self.sanitized_package_name
        self.package_source.save()

        self.build_record.logger.debug('Detecting Build dependencies')
        self.build_dependencies += self.detect_build_dependencies()
        self.build_record.logger.info('Build dependencies: %s' % (', '.join(self.build_dependencies)))

        self.build_record.logger.debug('Detecting run-time dependencies')
        self.runtime_dependencies += self.detect_runtime_dependencies()
        self.build_record.logger.info('Runtime dependencies: %s' % (', '.join(self.runtime_dependencies)))

        self.populate_debian_dir()

        self.add_changelog_entry()

        self.build_external_dependency_repo_keys()
        self.build_external_dependency_repo_sources()
        self.docker_build_source_package()
        self.docker_build_binary_package()
        self.build_record.build_finished = timezone.now()
        self.build_record.save()

    def build_external_dependency_repo_keys(self):
        """create a file which has all external dependency repos keys"""
        extdeps = self.package_source.series.externaldependency_set.all()
        if extdeps:
            with open(os.path.join(self.basedir, 'keys'), 'w') as fp:
                for extdep in extdeps:
                    if extdep.key:
                        fp.write(extdep.key)

    def build_external_dependency_repo_sources(self):
        """create a file which has all external dependency repo sources"""
        lines = [self.package_source.series.binary_source_list(force_trusted=True)]
        lines += [extdep.deb_line for extdep in self.package_source.series.externaldependency_set.all()]
        with open(os.path.join(self.basedir, 'repos'), 'w') as fp:
            fp.write('\n'.join(lines))

    def docker_build_source_package(self):
        """Build source package in docker"""
        source_dir = os.path.basename(self.builddir)
        with open(self.build_record.buildlog(), 'a+') as fp:
            try:
                stdout_orig = sys.stdout
                sys.stdout = fp
                get_build_backend().source_build(self.basedir, source_dir)
            finally:
                sys.stdout = stdout_orig

    def docker_build_binary_package(self):
        """Build binary packages in docker"""
        parallel = self.get_build_config().get('parallel',
                                               getattr(settings, 'AASEMBLE_BUILDSVC_DEFAULT_PARALLEL', 1))
        with open(self.build_record.buildlog(), 'a+') as fp:
            try:
                stdout_orig = sys.stdout
                sys.stdout = fp
                get_build_backend().binary_build(self.basedir, parallel=parallel)
            finally:
                sys.stdout = stdout_orig

    def get_build_config(self):
        return self.get_aasemble_config().get('build', {})

    def get_aasemble_config(self):
        aasemble_config = os.path.join(self.builddir, '.aasemble.yml')
        if os.path.exists(aasemble_config):
            with open(aasemble_config, 'r') as fp:
                return yaml.load(fp)
        return {}

    def detect_runtime_dependencies(self):
        return []

    def detect_build_dependencies(self):
        reqfile = os.path.join(self.builddir, '.extra_build_packages')
        build_deps = []
        if os.path.exists(reqfile):
            with open(reqfile, 'r') as fp:
                build_deps += filter(lambda s: s, fp.read().split('\n'))

        build_deps += self.get_aasemble_config().get('build', {}).get('dependencies', [])
        return []

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
                epoch = epoch + 1

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
    for builder in PackageBuilderRegistry.builders:
        if builder.is_suitable(path):
            return builder

from . import debian  # noqa
from . import python  # noqa
from . import golang  # noqa
from . import generic  # noqa
