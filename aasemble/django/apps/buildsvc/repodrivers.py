import logging
import os.path

import deb822

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.module_loading import import_string

import gnupg

from aasemble.django.utils import recursive_render
from aasemble.utils import ensure_dir, run_cmd

LOG = logging.getLogger(__name__)


class RepositorySignatureDriver(object):
    EXPIRE_DATE_NEVER_EXPIRES = 0

    def __init__(self, home=None):
        if home is None:
            home = self.get_default_gpghome()

        self.gnupg = gnupg.GPG(gnupghome=home)

    def get_default_gpghome(self):
        return getattr(settings, 'BUILDSVC_GPGHOME', None)

    def key_generation_data_for_repository(self, repository):
        return render_to_string('buildsvc/gpg-keygen-input.tmpl',
                                {'repository': repository})

    def generate_key(self, repository):
        input_data = self.key_generation_data_for_repository(repository)
        generated_key = self.gnupg.gen_key(input_data)
        return generated_key.fingerprint[-8:]

    def key_data(self, repository):
        if repository.key_id:
            return self.gnupg.export_keys([repository.key_id])


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
        self.reposity_signature_driver = RepositorySignatureDriver()

    def ensure_key(self):
        if not self.repository.key_id:
            self.repository.key_id = self.generate_key()
            self.repository.save()
        if not self.repository.key_data:
            self.repository.key_data = self.repository._key_data()
            self.repository.save()


class RepreproDriver(RepositoryDriver):
    def generate_key(self):
        return self.reposity_signature_driver.generate_key(self.repository)

    def key_data(self):
        return self.reposity_signature_driver.key_data(self.repository)

    @property
    def basedir(self):
        basedir = os.path.join(settings.BUILDSVC_REPOS_BASE_DIR,
                               self.repository.user.username, self.repository.name)
        return ensure_dir(basedir)

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
        recursive_render(tmpl_dir, self.basedir, {'repository': self.repository})

    def export_key(self):
        keypath = os.path.join(self.repository.outdir(), 'repo.key')
        if not os.path.exists(keypath):
            with open(keypath, 'w') as fp:
                fp.write(self.repository.key_data)

    def _reprepro(self, *args):
        return run_cmd(['reprepro', '-b', self.basedir, '--waitforlock=10'] + list(args))

def get_repo_driver(repository):
    driver_name = getattr(settings, 'BUILDSVC_REPODRIVER', 'aasemble.django.apps.buildsvc.repodrivers.RepreproDriver')
    driver = import_string(driver_name)
    return driver(repository)
