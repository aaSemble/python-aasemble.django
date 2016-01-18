from __future__ import absolute_import

import argparse

import json
import logging
import os
import sys

import dbuild

from debian.debian_support import version_compare

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

import requests

import yaml

LOG = logging.getLogger(__name__)


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


def fetch_build_http(url):
    return requests.get(url).json()


def fetch_build_file(path):
    with open(path, 'r') as fp:
        return json.load(fp)


def fetch_build(build_id):
    if build_id.startswith('http://') or build_id.startswith('https://'):
        return fetch_build_http(build_id)
    elif os.path.exists(build_id):
        return fetch_build_file(build_id)
    return None


class PackageBuilder(object):
    def __init__(self, basedir, build_record):
        self.basedir = basedir
        self.build_dependencies = []
        self.runtime_dependencies = []
        self.build_record = fetch_build(build_record)
        self.logger = LOG

    @property
    def builddir(self):
        return os.path.join(self.basedir, 'build')

    def get_version(self):
        """Derive version from code, fallback to build_counter"""
        return self.build_record['build_counter']

    def build(self):
        self.logger.debug('Using %s to build' % (type(self)))

        self.logger.debug('Detecting Build dependencies')
        self.build_dependencies += self.detect_build_dependencies()
        self.logger.info('Build dependencies: %s' % (', '.join(self.build_dependencies)))

        self.logger.debug('Detecting run-time dependencies')
        self.runtime_dependencies += self.detect_runtime_dependencies()
        self.logger.info('Runtime dependencies: %s' % (', '.join(self.runtime_dependencies)))

        self.populate_debian_dir()

        self.add_changelog_entry()

        self.build_external_dependency_repo_keys()
        self.build_external_dependency_repo_sources()
        self.docker_build_source_package()
        self.docker_build_binary_package()

    def build_external_dependency_repo_keys(self):
        """create a file which has all external dependency repos keys"""
        with open(os.path.join(self.basedir, 'keys'), 'wb') as fp:
            fp.write(requests.get(self.build_record['source']['repository_info']['build_apt_keys']).content)

    def build_external_dependency_repo_sources(self):
        """create a file which has all external dependency repo sources"""
        with open(os.path.join(self.basedir, 'repos'), 'wb') as fp:
            fp.write(requests.get(self.build_record['source']['repository_info']['build_sources_list']).content)

    def docker_build_source_package(self):
        """Build source package in docker"""
        source_dir = os.path.basename(self.builddir)
        get_build_backend().source_build(self.basedir, source_dir)

    def docker_build_binary_package(self):
        """Build binary packages in docker"""
        parallel = self.get_build_config().get('parallel',
                                               getattr(settings, 'AASEMBLE_BUILDSVC_DEFAULT_PARALLEL', 1))
        get_build_backend().binary_build(self.basedir, parallel=parallel)

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
        from ....utils import recursive_render

        self.logger.debug('Populating debian dir')
        recursive_render(os.path.join(os.path.dirname(__file__), '../templates/buildsvc/debian'),
                         os.path.join(self.builddir, 'debian'),
                         {'pkgname': self.sanitized_package_name,
                          'builder': self}, logger=self.logger)

    @property
    def env(self):
        return {'DEBEMAIL': settings.BUILDSVC_DEBEMAIL,
                'DEBFULLNAME': settings.BUILDSVC_DEBFULLNAME}

    def add_changelog_entry(self):
        fmt = '%a, %d %b %Y %H:%M:%S %z'
        rendered = render_to_string('buildsvc/changelog.deb',
                                    {'pkgname': self.sanitized_package_name,
                                     'version': self.package_version,
                                     'distribution': self.build_record['source']['repository_info']['series_name'],
                                     'full_name': self.env['DEBFULLNAME'],
                                     'email': self.env['DEBEMAIL'],
                                     'timestamp': timezone.now().strftime(fmt)})

        self.logger.info('New changelog entry: %s' % (rendered,))
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
        return self.build_record['source']['repository_info']['name']

    @property
    def package_version(self):
        native_version = self.native_version
        if native_version:
            version = '%s+%d' % (native_version, self.build_record['build_counter'])
        else:
            version = '%d' % (self.build_record['build_counter'],)

        epoch = 0

        last_built_version = self.build_record['source']['last_built_version']
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


def main(argv=sys.argv[1:]):
    if not settings.configured:
        settings.configure()

    parser = argparse.ArgumentParser()
    parser.add_argument('--basedir', default=os.getcwd(), help='Base directory [default="."]')
    parser.add_argument('action', choices=['build', 'name', 'version'])
    parser.add_argument('build_record', help='build_record ID (URL)')

    options = parser.parse_args(argv)

    from . import debian  # noqa
    from . import python  # noqa
    from . import golang  # noqa
    from . import generic  # noqa

    builder_class = choose_builder(options.basedir + '/build')
    builder = builder_class(options.basedir, options.build_record)
    if options.action == 'version':
        sys.stdout.write(builder.package_version)
    elif options.action == 'name':
        sys.stdout.write(builder.sanitized_package_name)
    elif options.action == 'build':
        builder.build()
    else:
        assert False, 'Invalid action provided'

if __name__ == '__main__':
    sys.exit(not main(sys.argv[1:]))
