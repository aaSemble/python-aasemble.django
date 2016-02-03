import logging
import os.path

import deb822

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.module_loading import import_string

from aasemble.django.utils import recursive_render
from aasemble.utils import run_cmd

LOG = logging.getLogger(__name__)


def remove_ddebs_from_changes(changes_file):
    with open(changes_file, 'r') as fp:
        changes = deb822.Changes(fp)

    for section in ('Checksums-Sha1', 'Checksums-Sha256', 'Files'):
        if section not in changes:
            continue
        new_section = [f for f in changes[section] if not f['name'].endswith('.ddeb')]
        changes[section] = new_section

    with open(changes_file, 'w') as fp:
        fp.write(changes.dump())


class RepositoryDriver(object):
    def __init__(self, repository):
        self.repository = repository

    def ensure_key(self):
        if not self.repository.key_id:
            self.repository.key_id = self.generate_key()
            self.repository.save()
        if not self.repository.key_data:
            self.repository.key_data = self.repository._key_data()
            self.repository.save()


class FakeDriver(RepositoryDriver):
    def generate_key(self):
        return 'FAKEID'

    def key_data(self):
        return self.repository.key_id * 50

    def export(self):
        pass

    def process_changes(self, series_name, changes_file):
        pass


class RepreproDriver(RepositoryDriver):
    def generate_key(self):
        LOG.info('Generating key for %s' % (self.repository))
        gpg_input = render_to_string('buildsvc/gpg-keygen-input.tmpl',
                                     {'repository': self.repository})
        output = run_cmd(['gpg', '--batch', '--gen-key'], input=gpg_input)

        for l in output.split('\n'):
            if l.startswith('gpg: key '):
                return l.split(' ')[2]

    def key_data(self):
        if self.repository.key_id:
            env = {'GNUPG_HOME': self.gpghome()}
            return run_cmd(['gpg', '-a', '--export', self.repository.key_id], override_env=env)

    def gpghome(self):
        return os.path.join(self.repository.basedir, '.gnupg')

    def export(self):
        self.ensure_key()
        self.ensure_directory_structure()
        self.export_key()
        self._reprepro('export')

    def process_changes(self, series_name, changes_file):
        self.ensure_directory_structure()
        remove_ddebs_from_changes(changes_file)
        self._reprepro('--ignore=wrongdistribution', 'include', series_name, changes_file)
        self.export()

    def ensure_directory_structure(self):
        tmpl_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   'templates/buildsvc/reprepro'))
        recursive_render(tmpl_dir, self.repository.basedir, {'repository': self.repository})

    def export_key(self):
        keypath = os.path.join(self.repository.outdir(), 'repo.key')
        if not os.path.exists(keypath):
            with open(keypath, 'w') as fp:
                fp.write(self.repository.key_data)

    def _reprepro(self, *args):
        env = {'GNUPG_HOME': self.gpghome()}
        return run_cmd(['reprepro', '-b', self.repository.basedir, '--waitforlock=10'] + list(args),
                       override_env=env)


def get_repo_driver(repository):
    driver_name = getattr(settings, 'BUILDSVC_REPODRIVER', 'aasemble.django.apps.buildsvc.repodrivers.RepreproDriver')
    driver = import_string(driver_name)
    return driver(repository)
