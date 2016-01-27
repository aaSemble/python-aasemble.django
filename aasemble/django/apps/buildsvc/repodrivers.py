import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.module_loading import import_string

from aasemble.django.utils import run_cmd

LOG = logging.getLogger(__name__)


class RepositoryDriver(object):
    def __init__(self, repository):
        self.repository = repository


class FakeDriver(RepositoryDriver):
    def generate_key(self):
        return 'FAKEID'

    def key_data(self):
        return self.repository.key_id * 50


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
            env = {'GNUPG_HOME': self.repository.gpghome()}
            return run_cmd(['gpg', '-a', '--export', self.repository.key_id], override_env=env)


def get_repo_driver(repository):
    driver_name = getattr(settings, 'BUILDSVC_REPODRIVER', 'aasemble.django.apps.buildsvc.repodrivers.RepreproDriver')
    driver = import_string(driver_name)
    return driver(repository)
