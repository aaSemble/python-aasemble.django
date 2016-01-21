import os
import os.path

from django.conf import settings

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

from aasemble.django.utils import run_cmd, ssh_get, ssh_run_cmd


class Local(object):
    def __init__(self, name):
        pass

    def run_cmd(self, *args, **kwargs):
        return run_cmd(*args, **kwargs)

    def get(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class GCENode(object):
    def __init__(self, name):
        self.name = name
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            driver = get_driver(Provider.GCE)
            self._connection = driver(settings.AASEMBLE_BUILDSVC_GCE_SERVICE_ACCOUNT,
                                      settings.AASEMBLE_BUILDSVC_GCE_KEY_FILE,
                                      project=settings.AASEMBLE_BUILDSVC_GCE_PROJECT)
        return self._connection

    @property
    def _zone(self, settings=settings):
        return getattr(settings, 'AASEMBLE_BUILDSVC_GCE_ZONE', 'us-central1-f')

    @property
    def _machine_type_short(self):
        return getattr(settings, 'AASEMBLE_BUILDSVC_GCE_MACHINE_TYPE', 'n1-standard-4')

    @property
    def _ssh_public_key_file(self):
        default_ssh_public_key_file = os.path.expanduser('~/.ssh/id_rsa.pub')
        return getattr(settings, 'AASEMBLE_BUILDSVC_PUBLIC_KEY', default_ssh_public_key_file)

    @property
    def _ssh_public_key_data(self):
        with open(self._ssh_public_key_file, 'r') as fp:
            return fp.read()

    @property
    def _source_disk_image(self):
        return settings.AASEMBLE_BUILDSVC_GCE_IMAGE

    @property
    def _startup_script(self):
        with open(os.path.join(os.path.dirname(__file__), 'startup-script.sh'), 'r') as fp:
            return fp.read()

    @property
    def _disk_size(self, settings=settings):
        return getattr(settings, 'AASEMBLE_BUILDSVC_GCE_DISK_SIZE', 100)

    @property
    def _disks(self):
        return [{'boot': True,
                 'autoDelete': True,
                 'initializeParams': {
                     'sourceImage': self._source_disk_image,
                     'diskType': 'zones/%s/diskTypes/pd-ssd' % (self._zone,),
                     'diskSizeGb': self._disk_size}}]

    @property
    def _metadata(self):
        return {'startup-script': self._startup_script,
                'sshKeys': 'ubuntu:' + self._ssh_public_key_data}

    def launch(self):
        self.node = self.connection.create_node(name=self.name,
                                                size=self._machine_type_short,
                                                image=None,
                                                location=self._zone,
                                                ex_disks_gce_struct=self._disks,
                                                ex_metadata=self._metadata)

    @property
    def _ssh_connect_string(self):
        return 'ubuntu@%s' % (self.node.public_ips[0],)

    def run_cmd(self, *args, **kwargs):
        return ssh_run_cmd(self._ssh_connect_string, *args, remote_cwd='workspace', **kwargs)

    def get(self, shell_pattern, destdir):
        ssh_get(self._ssh_connect_string, 'workspace/{}'.format(shell_pattern), destdir)

    def destroy(self):
        self.node.destroy()

    def __enter__(self):
        self.launch()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.destroy()


def get_executor(name=None, settings=settings):
    if name is None:
        name = getattr(settings, 'AASEMBLE_BUILDSVC_EXECUTOR', 'Local')
    return globals()[name]
