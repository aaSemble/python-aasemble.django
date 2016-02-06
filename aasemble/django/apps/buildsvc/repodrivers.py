import gzip as gzipmod
import hashlib
import logging
import os.path
import tempfile

import deb822

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils.module_loading import import_string

import gnupg

from six import BytesIO

from aasemble.django.apps.buildsvc import storage
from aasemble.django.apps.buildsvc.models.binary_package_version import BinaryPackageVersion
from aasemble.django.apps.buildsvc.models.source_package_version import SourcePackageVersion
from aasemble.django.common.utils import user_has_feature
from aasemble.django.utils import recursive_render
from aasemble.utils import ensure_dir, run_cmd

LOG = logging.getLogger(__name__)


class RepositorySignatureDriver(object):
    EXPIRE_DATE_NEVER_EXPIRES = 0

    def __init__(self, home=None):
        self.gnupg = gnupg.GPG(gnupghome=self.get_default_gpghome())

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
            return self.gnupg.export_keys([repository.key_id]).encode('utf-8')

    def sign_inline(self, contents, key_id):
        return str(self.gnupg.sign(contents, keyid=key_id)).encode('utf-8')

    def get_signature(self, contents, key_id):
        fd, tmpfile = tempfile.mkstemp()
        try:
            os.close(fd)
            self.gnupg.sign(contents, detach=True, output=tmpfile, keyid=key_id)
            with open(tmpfile, 'rb') as fp:
                return fp.read()
        finally:
            os.unlink(tmpfile)


class FakeRepositorySignatureDriver(RepositorySignatureDriver):
    def generate_key(self, repository):
        return 'AB3368F7'

    def key_data(self, key_data):
        with open(os.path.join(os.path.dirname(__file__), 'test_data/eric6.public.key'), 'rb') as fp:
            return fp.read()

    def get_default_gpghome(self):
        retval = os.path.join(os.path.dirname(__file__), 'test_data/gpghome')
        os.chmod(retval, 0o0700)
        return retval


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
        self.reposity_signature_driver = get_repository_signature_driver()

    def ensure_key(self):
        if not self.repository.key_id:
            self.repository.key_id = self.generate_key()
            self.repository.save()
        if not self.repository.key_data:
            self.repository.key_data = self.key_data().decode('utf-8')
            self.repository.save()

    def generate_key(self):
        """Generates key if one does not already exist.

        Returns key ID"""
        raise NotImplementedError()

    def key_data(self):
        """Returns the public key data in ASCII armored format"""
        raise NotImplementedError()

    def export(self):
        """Writes all Packages, Sources, Release and key files

        This should take care of creating directory structures,
        config files, etc."""
        raise NotImplementedError()

    def import_deb(self, series_name, fpath):
        """Import deb into the given series

        Drivers should provide *either* import_dsc+import_deb *or*
        process_changes. Not both."""
        raise NotImplementedError()

    def import_dsc(self, series_name, fpath):
        """Import dsc into the given series

        Drivers should provide *either* import_dsc+import_deb *or*
        process_changes. Not both."""
        raise NotImplementedError()

    def process_changes(self, series_name, changes_file):
        """Process changes file into the given series

        Drivers should provide *either* import_dsc+import_deb *or*
        process_changes. Not both."""
        raise NotImplementedError()


class AasembleDriver(RepositoryDriver):
    def __init__(self, *args, **kwargs):
        self.storage = storage.get_repository_storage_driver()
        super(AasembleDriver, self).__init__(*args, **kwargs)

    def generate_key(self):
        return self.reposity_signature_driver.generate_key(self)

    def key_data(self):
        return self.reposity_signature_driver.key_data(self.repository)

    def get_metadata(self, contents):
        return {'size': len(contents),
                'md5': hashlib.md5(contents).hexdigest(),
                'sha1': hashlib.sha1(contents).hexdigest(),
                'sha256': hashlib.sha256(contents).hexdigest()}

    def store(self, path, contents, metadata, gzip=False, bzip2=False):
        metadata[path] = self.get_metadata(contents)
        self.storage.delete(path)
        self.storage.save(path, ContentFile(contents))
        if gzip:
            gzpath = path + '.gz'
            fp = BytesIO()
            with gzipmod.GzipFile(fileobj=fp, mode='wb') as gzfp:
                gzfp.write(contents)
                gzfp.close()
            metadata[gzpath] = self.get_metadata(fp.getvalue())
            self.storage.delete(gzpath)
            self.storage.save(gzpath, ContentFile(fp.getvalue()))
        if bzip2:
            bzpath = path + '.bz2'
            bzdata = bzip2.compress(contents)
            metadata[bzpath] = self.get_metadata(bzdata)
            self.storage.delete(bzpath)
            self.storage.save(bzpath, ContentFile(bzdata))

    def render_to_bytes(self, tmpl, **context):
        return render_to_string(os.path.join(os.path.dirname(__file__),
                                'templates/buildsvc/repodriver', tmpl),
                                context).encode('utf-8')

    def import_dsc(self, series_name, fpath):
        series = self.repository.series_set.get(name=series_name)
        SourcePackageVersion.import_file(series, fpath)

    def import_deb(self, series_name, fpath):
        series = self.repository.series_set.get(name=series_name)
        BinaryPackageVersion.import_file(series, fpath)

    def process_changes(self, series_name, changes_file):
        pass

    def export(self):
        self.ensure_key()
        metadata = {}
        repo_dir = os.path.join(self.repository.user.username,
                                self.repository.name)
        dists_dir = os.path.join(repo_dir, 'dists')
        for series in self.repository.series.all():
            series_dir = os.path.join(dists_dir,
                                      series.name)
            for component in ['main']:
                for architecture in ['amd64']:
                    arch_dir = os.path.join(series_dir, component,
                                            'binary-%s' % (architecture,))
                    self.store(os.path.join(arch_dir, 'Packages'),
                               self.render_to_bytes('Packages.tmpl',
                                                    series=series),
                               metadata, gzip=True)
                    self.store(os.path.join(arch_dir, 'Release'),
                               self.render_to_bytes('archrelease.tmpl',
                                                    series=series,
                                                    architecture=architecture,
                                                    component=component), metadata)
                for architecture in ['source']:
                    arch_dir = os.path.join(series_dir,
                                            component,
                                            architecture)
                    self.store(os.path.join(arch_dir, 'Sources'),
                               self.render_to_bytes('Sources.tmpl',
                                                    series=series),
                               metadata=metadata, gzip=True)
                    self.store(os.path.join(arch_dir, 'Release'),
                               self.render_to_bytes('archrelease.tmpl',
                                                    series=series,
                                                    architecture=architecture,
                                                    component=component), metadata)

            strip_len = len(series_dir) + 1

            files = []
            for f in sorted(metadata.keys()):
                metadata[f]['path'] = f[strip_len:]
                files.append(metadata[f])

            release_data = self.render_to_bytes('distrelease.tmpl', series=series, files=files)

            self.store(os.path.join(series_dir, 'InRelease'),
                       self.reposity_signature_driver.sign_inline(release_data, series.repository.key_id), metadata)
            self.store(os.path.join(series_dir, 'Release'),
                       release_data, metadata)
            self.store(os.path.join(series_dir, 'Release.gpg'),
                       self.reposity_signature_driver.get_signature(release_data, series.repository.key_id), metadata)
            repo_file = os.path.join(repo_dir, 'repo.key')
            if not self.storage.exists(repo_file):
                self.storage.save(repo_file, ContentFile(self.repository.key_data))


class RepreproDriver(RepositoryDriver):
    def generate_key(self):
        return self.reposity_signature_driver.generate_key(self.repository)

    def key_data(self):
        return self.reposity_signature_driver.key_data(self.repository)

    def export(self):
        self.ensure_key()
        self.ensure_directory_structure()
        self.export_key()
        self._reprepro('export')

    def ensure_directory_structure(self):
        tmpl_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   'templates/buildsvc/reprepro'))
        recursive_render(tmpl_dir, self.basedir, {'repository': self.repository})

    def export_key(self):
        keypath = os.path.join(self.outdir, 'repo.key')
        if not os.path.exists(keypath):
            with open(keypath, 'wb') as fp:
                fp.write(self.repository.key_data.encode('utf-8'))

    @property
    def basedir(self):
        basedir = os.path.join(settings.BUILDSVC_REPOS_BASE_DIR,
                               self.repository.user.username, self.repository.name)
        return ensure_dir(basedir)

    @property
    def outdir(self):
        outdir = os.path.join(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR,
                              self.repository.user.username, self.repository.name)
        return ensure_dir(outdir)

    def import_dsc(self, series_name, fpath):
        pass

    def import_deb(self, series_name, fpath):
        pass

    def process_changes(self, series_name, changes_file):
        self.ensure_directory_structure()
        remove_ddebs_from_changes(changes_file)
        self._reprepro('--ignore=wrongdistribution', 'include', series_name, changes_file)
        self.export()

    def _reprepro(self, *args):
        return run_cmd(['reprepro', '-b', self.basedir, '--waitforlock=10'] + list(args),
                       override_env={'GNUPGHOME': self.reposity_signature_driver.get_default_gpghome()})


def get_repository_signature_driver():
    if getattr(settings, 'AASEMBLE_BUILDSVC_USE_FAKE_SIGNATURE_DRIVER', False):
        return FakeRepositorySignatureDriver()
    else:
        return RepositorySignatureDriver()


def get_repo_driver(repository):
    driver_name = getattr(settings, 'BUILDSVC_REPODRIVER', 'aasemble.django.apps.buildsvc.repodrivers.RepreproDriver')

    if user_has_feature(repository.user, 'BUILDSVC_INTERNAL_REPOSITORY_DRIVER'):
        driver_name = 'aasemble.django.apps.buildsvc.repodrivers.AasembleDriver'

    driver = import_string(driver_name)
    return driver(repository)
