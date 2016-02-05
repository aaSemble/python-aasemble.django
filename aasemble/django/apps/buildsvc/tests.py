import gzip
import os.path
import shutil
import subprocess
import sys
import tempfile

import deb822

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db.utils import IntegrityError
from django.test import override_settings
from django.test.utils import skipIf

import github3

import mock

from six import StringIO

from aasemble.django.apps.buildsvc import executors, repodrivers
from aasemble.django.apps.buildsvc.models import BinaryPackage, BinaryPackageVersion, BuildRecord, PackageSource, Repository, Series, SourcePackage, SourcePackageVersion, SourcePackageVersionFile
from aasemble.django.apps.buildsvc.models.package_source import NotAValidGithubRepository
from aasemble.django.apps.buildsvc.models.source_package_version_file import SOURCE_PACKAGE_FILE_TYPE_DSC, SOURCE_PACKAGE_FILE_TYPE_NATIVE
from aasemble.django.tests import AasembleLiveServerTestCase as LiveServerTestCase
from aasemble.django.tests import AasembleTestCase as TestCase
from aasemble.utils import run_cmd
from aasemble.utils.exceptions import CommandFailed


try:
    subprocess.check_call(['docker', 'ps'])
    docker_available = True
except:
    docker_available = False


class PkgBuildTestCase(LiveServerTestCase):
    @skipIf(not docker_available, 'Docker unavailable')
    def _test_build_debian(self):
        from . import pkgbuild

        tmpdir = tempfile.mkdtemp()
        try:
            source = PackageSource.objects.get(id=1)
            br = BuildRecord(source=source, build_counter=10, sha='e65b55054c5220321c56bb3dfa96fbe5199f329c')
            br.save()

            basedir = os.path.join(tmpdir, 'd')
            shutil.copytree(os.path.join(os.path.dirname(__file__), 'test_data', 'debian'), basedir)

            orig_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                pkgbuild.main(['--basedir', basedir, 'version', self.live_server_url + br.get_absolute_url()])
                self.assertEquals(sys.stdout.getvalue(), '0.1+10')
                sys.stdout = StringIO()

                pkgbuild.main(['--basedir', basedir, 'name', self.live_server_url + br.get_absolute_url()])
                self.assertEquals(sys.stdout.getvalue(), 'buildsvctest')

                pkgbuild.main(['--basedir', basedir, 'build', self.live_server_url + br.get_absolute_url()])
            finally:
                sys.stdout = orig_stdout

            self.assertTrue(os.path.exists(os.path.join(basedir, 'buildsvctest_0.1+10_source.changes')))
            self.assertTrue(os.path.exists(os.path.join(basedir, 'buildsvctest_0.1+10_amd64.changes')))
        finally:
            shutil.rmtree(tmpdir)


class RepositoryTestCase(TestCase):
    def test_unicode(self):
        repo = Repository.objects.get(id=12)
        self.assertEquals(str(repo), 'eric/eric5')

    def test_build_apt_keys(self):
        repo = Repository.objects.get(id=1)
        self.assertEquals(repo.first_series().build_apt_keys(),
                          'FAKE KEY for CA62552B\nFAKE KEY DATA for http://example.com/')

    def test_build_sources_list(self):
        repo = Repository.objects.get(id=1)
        self.assertEquals(repo.first_series().build_sources_list(),
                          'deb http://archive.ubuntu.com/ubuntu trusty main universe restricted multiverse\n'
                          'deb http://archive.ubuntu.com/ubuntu trusty-updates main universe restricted multiverse\n'
                          'deb http://archive.ubuntu.com/ubuntu trusty-security main universe restricted multiverse\n'
                          'deb [trusted=yes] http://127.0.0.1:8000/apt/brandon/brandon aasemble main\n'
                          'deb http://example.com/ubuntu trusty main universe\n'
                          'deb http://example.com/ubuntu trusty-updates main universe')

    def test_lookup_by_user_with_extra_admin(self):
        charles = auth_models.User.objects.get(id=3)
        self.assertEquals(set([2, 3]), set([repo.id for repo in Repository.lookup_by_user(charles)]))

    def test_lookup_by_user_without_extra_admin(self):
        frank = auth_models.User.objects.get(id=4)
        self.assertEquals(set([3]), set([repo.id for repo in Repository.lookup_by_user(frank)]))

    def test_lookup_by_user_with_multiple_groups(self):
        brandon = auth_models.User.objects.get(id=2)
        self.assertEquals(set([1, 3]), set([repo.id for repo in Repository.lookup_by_user(brandon)]))

    def test_lookup_by_deactive_user_not_possible(self):
        frank = auth_models.User.objects.get(id=6)
        self.assertEquals(set(), set([repo.id for repo in Repository.lookup_by_user(frank)]))

    def test_user_can_modify_own_repo(self):
        eric = auth_models.User.objects.get(id=5)
        self.assertTrue(Repository.objects.get(id=4).user_can_modify(eric))
        self.assertTrue(Repository.objects.get(id=12).user_can_modify(eric))

    def test_super_user_can_modify_repo(self):
        george = auth_models.User.objects.get(id=7)
        self.assertTrue(Repository.objects.get(id=4).user_can_modify(george))

    def test_extra_admin_user_modify_repo(self):
        brandon = auth_models.User.objects.get(id=2)
        self.assertTrue(Repository.objects.get(id=3).user_can_modify(brandon))

    def test_user_can_modify_other_repo(self):
        charles = auth_models.User.objects.get(id=3)
        self.assertTrue(Repository.objects.get(id=3).user_can_modify(charles))

    def test_user_can_not_modify_other_repo(self):
        brandon = auth_models.User.objects.get(id=2)
        self.assertFalse(Repository.objects.get(id=12).user_can_modify(brandon))

    def test_user_same_group_can_modify_other_repo(self):
        brandon = auth_models.User.objects.get(id=2)
        self.assertFalse(Repository.objects.get(id=2).user_can_modify(brandon))

    def test_deactivated_super_user_can_not_modify_own_repo(self):
        harold = auth_models.User.objects.get(id=8)
        self.assertFalse(Repository.objects.get(id=8).user_can_modify(harold))

    def test_first_series(self):
        """
        What exactly constitutes the "first" series is poorly defined.
        Right now, there can only be one series, so that makes the test easier
        """
        repo = Repository.objects.get(id=1)
        series = Series.objects.get(id=1)
        self.assertEquals(repo.first_series(), series)

    @override_settings(BUILDSVC_DEFAULT_SERIES_NAME='somethingelse')
    def test_first_series_does_not_create_extra_series_when_default_is_renamed(self):
        repo = Repository.objects.get(id=1)

        repo.first_series()

        self.assertEquals(repo.series.count(), 1)

    @override_settings(BUILDSVC_DEFAULT_SERIES_NAME='somethingelse')
    def test_first_series_creates_series_when_there_is_not_one_already(self):
        repo = Repository.objects.create(user_id=1, name='reponame')
        self.assertEquals(repo.series.count(), 0)

        series = repo.first_series()
        self.assertEquals(series.repository, repo)
        self.assertEquals(series.name, 'somethingelse')

    def test_unique_reponame_raises_integrity_error(self):
        self.assertRaises(IntegrityError, Repository.objects.create, user_id=5, name='eric4')

    @override_settings(BUILDSVC_REPOS_BASE_PUBLIC_DIR='/some/public/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.repository.ensure_dir', lambda s: s)
    def test_buildlogdir(self):
        repo = Repository.objects.get(id=12)
        self.assertEquals(repo.buildlogdir, '/some/public/dir/eric/eric5/buildlogs')

    @mock.patch('aasemble.django.apps.buildsvc.models.repository.get_repo_driver')
    def test_export(self, get_repo_driver):
        repo = Repository.objects.get(id=2)
        repo.export()
        get_repo_driver.return_value.export.assert_called_with()

    @mock.patch('aasemble.django.apps.buildsvc.models.repository.get_repo_driver')
    def test_process_changes(self, get_repo_driver):
        repo = Repository.objects.get(id=2)
        repo.process_changes('someseries', 'somefile')
        get_repo_driver.return_value.process_changes.assert_called_with('someseries', 'somefile')

    @override_settings(BUILDSVC_REPOS_BASE_URL='http://example.com/some/dir')
    def test_baseurl(self):
        repo = Repository.objects.get(id=12)
        self.assertEquals(repo.base_url, 'http://example.com/some/dir/eric/eric5')


class PackageSourceTestCase(TestCase):
    @mock.patch('aasemble.django.apps.buildsvc.tasks.reprepro')
    def test_post_delete(self, reprepro):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://example.com/git',
                                          branch='master',
                                          last_built_name='something')
        ps.delete()
        reprepro.delay.assert_called_with(1, 'removesrc', 'aasemble', 'something')

    def test_github_owner_repo(self):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://github.com/owner/repo',
                                          branch='master',
                                          last_built_name='something')
        self.assertEquals(('owner', 'repo'), ps.github_owner_repo())

    def test_github_owner_repo_strips_dot_git(self):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://github.com/owner/repo.git',
                                          branch='master',
                                          last_built_name='something')
        self.assertEquals(('owner', 'repo'), ps.github_owner_repo())

    def test_github_owner_repo_not_github(self):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://example.com/git',
                                          branch='master',
                                          last_built_name='something')
        self.assertRaises(NotAValidGithubRepository, ps.github_owner_repo)

    def test_github_owner_repo_too_many_parts(self):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://github.com/part1/part2/part3',
                                          branch='master',
                                          last_built_name='something')
        self.assertRaises(NotAValidGithubRepository, ps.github_owner_repo)

    def test_github_owner_repo_too_few_parts(self):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://github.com/part1',
                                          branch='master',
                                          last_built_name='something')
        self.assertRaises(NotAValidGithubRepository, ps.github_owner_repo)

    @mock.patch('github3.GitHub')
    @override_settings(AASEMBLE_BUILDSVC_USE_WEBHOOKS=False)
    def test_register_webhook_disabled(self, GitHub):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://github.com/owner/repo',
                                          branch='master',
                                          last_built_name='something')

        ps.register_webhook()

        GitHub.assert_not_called()

    @mock.patch('github3.GitHub')
    @override_settings(GITHUB_WEBHOOK_URL='https://example.com/api/github/')
    @override_settings(AASEMBLE_BUILDSVC_USE_WEBHOOKS=True)
    def test_register_webhook(self, GitHub):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://github.com/owner/repo',
                                          branch='master',
                                          last_built_name='something')

        self.assertFalse(ps.webhook_registered)
        ps.register_webhook()

        GitHub.assert_called_with(token='2348562349569324875692387562364598732645')

        connection = GitHub.return_value
        connection.repository.assert_called_with('owner', 'repo')

        repository = connection.repository.return_value
        repository.create_hook.assert_called_with(name='web',
                                                  config={'url': 'https://example.com/api/github/',
                                                          'content_type': 'json'})
        ps.refresh_from_db()
        self.assertTrue(ps.webhook_registered)

    @mock.patch('github3.GitHub')
    @override_settings(GITHUB_WEBHOOK_URL='https://example.com/api/github/')
    @override_settings(AASEMBLE_BUILDSVC_USE_WEBHOOKS=True)
    def test_register_webhook_fails_does_not_update_db(self, GitHub):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://github.com/owner/repo',
                                          branch='master',
                                          last_built_name='something')

        self.assertFalse(ps.webhook_registered)

        connection = GitHub.return_value
        repository = connection.repository.return_value
        repository.create_hook.return_value = None

        ps.register_webhook()

        connection.repository.assert_called_with('owner', 'repo')
        repository.create_hook.assert_called_with(name='web',
                                                  config={'url': 'https://example.com/api/github/',
                                                          'content_type': 'json'})

        ps.refresh_from_db()
        self.assertFalse(ps.webhook_registered)

    @mock.patch('github3.GitHub')
    @override_settings(GITHUB_WEBHOOK_URL='https://example.com/api/github/')
    @override_settings(AASEMBLE_BUILDSVC_USE_WEBHOOKS=True)
    def test_register_webhook_already_registered_updates_db(self, GitHub):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://github.com/owner/repo',
                                          branch='master',
                                          last_built_name='something')

        self.assertFalse(ps.webhook_registered)

        class Response(object):
            status_code = 422

            def json(self):
                return {u'documentation_url': u'https://developer.github.com/v3/repos/hooks/#create-a-hook',
                        u'errors': [{u'code': u'custom',
                                     u'message': u'Hook already exists on this repository',
                                     u'resource': u'Hook'}],
                        u'message': u'Validation Failed'}

        connection = GitHub.return_value
        repository = connection.repository.return_value
        repository.create_hook.return_value = github3.GitHubError(Response())

        ps.register_webhook()

        connection.repository.assert_called_with('owner', 'repo')
        repository.create_hook.assert_called_with(name='web',
                                                  config={'url': 'https://example.com/api/github/',
                                                          'content_type': 'json'})

        ps.refresh_from_db()
        self.assertTrue(ps.webhook_registered)

    @mock.patch('github3.GitHub')
    @override_settings(GITHUB_WEBHOOK_URL='https://example.com/api/github/')
    def test_register_webhook_noop_if_already_registered(self, GitHub):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://github.com/owner/repo',
                                          branch='master',
                                          last_built_name='something',
                                          webhook_registered=True)

        self.assertTrue(ps.register_webhook())
        GitHub.assert_not_called()

    @mock.patch('aasemble.django.apps.buildsvc.models.package_source.run_cmd')
    def test_poll_no_changes(self, run_cmd):
        run_cmd.return_value = b'cdf46dc0-a49c-11e5-b00a-c712eaff3d7b	refs/heads/master\n'
        ps = PackageSource.objects.get(id=1)
        self.assertFalse(ps.poll())
        run_cmd.assert_called_with(['git', 'ls-remote', 'https://github.com/eric/project0', 'refs/heads/master'])

    @mock.patch('aasemble.django.apps.buildsvc.models.package_source.run_cmd')
    def test_poll_changes(self, run_cmd):
        run_cmd.return_value = b'cdf46dc0-a49c-11e5-b00a-c712eaff3d7c	refs/heads/master\n'
        ps = PackageSource.objects.get(id=1)
        self.assertTrue(ps.poll())
        run_cmd.assert_called_with(['git', 'ls-remote', 'https://github.com/eric/project0', 'refs/heads/master'])

    @mock.patch('aasemble.django.apps.buildsvc.models.package_source.run_cmd')
    def test_poll_fails(self, run_cmd):
        run_cmd.side_effect = CommandFailed("['git', 'ls-remote', u'https://github.com/eric/project0', u'refs/heads/master'] "
                                            "returned 128. Output: fatal: could not read Username for 'https://github.com': "
                                            "No such device or address\n",
                                            ['git', 'ls-remote', u'https://github.com/eric/project0', u'refs/heads/master'], 128,
                                            "fatal: could not read Username for 'https://github.com': No such device or address\n")
        ps = PackageSource.objects.get(id=1)
        self.assertFalse(ps.poll())
        run_cmd.assert_called_with(['git', 'ls-remote', 'https://github.com/eric/project0', 'refs/heads/master'])
        self.assertTrue(ps.disabled)
        self.assertTrue(ps.last_failure_time)
        self.assertEquals(ps.last_failure, "fatal: could not read Username for 'https://github.com': No such device or address\n")

    @mock.patch('aasemble.django.apps.buildsvc.tasks.build')
    def test_build(self, build):
        ps = PackageSource.objects.get(id=1)
        ps.build()
        build.delay.assert_called_with(1)

    @mock.patch('aasemble.django.apps.buildsvc.executors.run_cmd')
    def test_build_real(self, run_cmd):
        def run_cmd_side_effect(cmd, *args, **kwargs):
            if cmd[0] == 'timeout':
                return ''
            if cmd[0] == 'aasemble-pkgbuild':
                if cmd[1] == 'version':
                    return '124'
                if cmd[1] == 'name':
                    return 'detectedname'
                if 'build' in cmd[1:]:
                    return ''
                if cmd[1] == 'checkout':
                    return ''
            raise Exception('Unexpected command')

        run_cmd.side_effect = run_cmd_side_effect
        ps = PackageSource.objects.get(id=7)
        ps.build_real()


class ExecutorTestCase(TestCase):
    @mock.patch('aasemble.django.apps.buildsvc.executors.GCENode.destroy')
    @mock.patch('aasemble.django.apps.buildsvc.executors.GCENode.launch')
    def test_gce_node(self, launch, destroy):
        with executors.GCENode('node-name'):
            launch.assert_called_with()
            destroy.assert_not_called()
        destroy.assert_called_with()

    def test_get_executor_default(self):
        self.assertEquals(executors.get_executor_class(), executors.Local)

    def test_get_executor_specific(self):
        self.assertEquals(executors.get_executor_class('GCENode'), executors.GCENode)

    def test_get_executor_override_default(self):
        class Settings(object):
            AASEMBLE_BUILDSVC_EXECUTOR = 'GCENode'
        self.assertEquals(executors.get_executor_class(settings=Settings()), executors.GCENode)


class RepoDriverTestCase(object):
    @mock.patch('aasemble.django.apps.buildsvc.repodrivers.RepositorySignatureDriver.generate_key')
    def test_ensure_key_noop_when_key_id_set(self, generate_key):
        repo = Repository.objects.get(id=1)
        self.driver(repo).ensure_key()
        assert not generate_key.called

    @override_settings(AASEMBLE_BUILDSVC_USE_FAKE_SIGNATURE_DRIVER=True)
    def test_export(self):
        tmpdir = tempfile.mkdtemp()
        try:
            privatedir = os.path.join(tmpdir, 'private')
            publicdir = os.path.join(tmpdir, 'public')
            with self.settings(BUILDSVC_REPOS_BASE_DIR=privatedir,
                               BUILDSVC_REPOS_BASE_PUBLIC_DIR=publicdir):
                repo = Repository.objects.get(id=13)
                self.driver(repo).export()

                base_dir = os.path.join(publicdir, 'eric', 'eric6')
                assert os.path.isdir(base_dir)

                dists_dir = os.path.join(base_dir, 'dists')
                assert os.path.isdir(dists_dir)

                binary_amd64_dir = os.path.join(dists_dir, 'aasemble', 'main', 'binary-amd64')
                assert os.path.isdir(binary_amd64_dir)

                packages_file = os.path.join(binary_amd64_dir, 'Packages')

                with open(packages_file, 'r') as fp:
                    self.assertEquals(fp.read(), '')

                packages_gz_file = os.path.join(binary_amd64_dir, 'Packages.gz')
                with gzip.open(packages_gz_file, 'rb') as fp:
                    self.assertEquals(fp.read(), b'')

                binary_amd64_release_file = os.path.join(binary_amd64_dir, 'Release')
                with open(binary_amd64_release_file, 'r') as fp:
                    self.assertEquals(fp.read(), '''Archive: aasemble
Component: main
Origin: Eric6
Label: Eric6
Architecture: amd64
Description: eric6 aasemble
''')
                sources_dir = os.path.join(dists_dir, 'aasemble', 'main', 'source')
                assert os.path.isdir(sources_dir)

                sources_gz_file = os.path.join(sources_dir, 'Sources.gz')
                with gzip.open(sources_gz_file, 'rb') as fp:
                    self.assertEquals(fp.read(), b'')

                sources_release_file = os.path.join(sources_dir, 'Release')
                with open(sources_release_file, 'r') as fp:
                    self.assertEquals(fp.read(), '''Archive: aasemble
Component: main
Origin: Eric6
Label: Eric6
Architecture: source
Description: eric6 aasemble
''')

                gpghome = self.driver(repo).reposity_signature_driver.get_default_gpghome()
                inrelease_file = os.path.join(dists_dir, 'aasemble', 'InRelease')
                run_cmd(['gpg', '--verify', inrelease_file],
                        override_env={'GNUPGHOME': gpghome})

                with open(inrelease_file, 'r') as fp:
                    lines = [l.rstrip('\n') for l in fp.readlines()]

                sepline = lines.index('-----BEGIN PGP SIGNATURE-----')
                body = '\n'.join(lines[3:sepline]) + '\n'

                release_file = os.path.join(dists_dir, 'aasemble', 'Release')
                with open(release_file, 'r') as fp:
                    self.assertEquals(fp.read(), body)

                release_gpg_file = os.path.join(dists_dir, 'aasemble', 'Release.gpg')

                run_cmd(['gpg', '--verify', release_gpg_file, release_file],
                        override_env={'GNUPGHOME': gpghome})

                with open(os.path.join(base_dir, 'repo.key'), 'r') as fp1:
                    with open(os.path.join(os.path.dirname(__file__), 'test_data', 'eric6.public.key')) as fp2:
                        self.assertEquals(fp1.read(), fp2.read())
        finally:
            shutil.rmtree(tmpdir)


class RepreproRepoDriverTestCase(TestCase, RepoDriverTestCase):
    driver = repodrivers.RepreproDriver

    @mock.patch('aasemble.django.apps.buildsvc.repodrivers.remove_ddebs_from_changes')
    def test_process_changes(self, remove_ddebs_from_changes):
        repo = mock.MagicMock()
        repodriver = self.driver(repo)
        with mock.patch.multiple(repodriver,
                                 export=mock.DEFAULT,
                                 ensure_directory_structure=mock.DEFAULT,
                                 _reprepro=mock.DEFAULT) as mocks:

            # Ensure that ensure_directory_structure() is called and ddebs are removed before _reprepro
            mocks['_reprepro'].side_effect = lambda *args: self.assertTrue(mocks['ensure_directory_structure'].called and remove_ddebs_from_changes.called)

            # Ensure that _reprepro() is called before export
            mocks['export'].side_effect = lambda: self.assertTrue(mocks['_reprepro'].called)

            repodriver.process_changes('myseries', '/path/to/changes')

            remove_ddebs_from_changes.assert_called_with('/path/to/changes')
            mocks['export'].assert_called_with()
            mocks['ensure_directory_structure'].ensure_called_with()
            mocks['_reprepro'].ensure_called_with('--ignore=wrongdistribution', 'include', 'myseries', '/path/to/changes')

    @mock.patch('aasemble.django.apps.buildsvc.repodrivers.ensure_dir', lambda s: s)
    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/public/dir')
    def test_ensure_directory_structure(self):
        with mock.patch('aasemble.django.apps.buildsvc.repodrivers.recursive_render') as recursive_render:
            repo = Repository.objects.get(id=12)
            repodriver = self.driver(repo)
            repodriver.ensure_directory_structure()

            srcdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates', 'buildsvc', 'reprepro'))
            dstdir = '/some/public/dir/eric/eric5'
            context = {'repository': repo}
            recursive_render.assert_called_with(srcdir, dstdir, context)

    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/dir')
    @mock.patch('aasemble.django.apps.buildsvc.repodrivers.ensure_dir', lambda s: s)
    def test_basedir(self):
        repo = Repository.objects.get(id=12)
        repodriver = self.driver(repo)
        self.assertEquals(repodriver.basedir, '/some/dir/eric/eric5')


class AasembleRepoDriverTestCase(TestCase, RepoDriverTestCase):
    driver = repodrivers.AasembleDriver


class ImportDscTestCase(TestCase):
    @override_settings(BUILDSVC_REPODRIVER='aasemble.django.apps.buildsvc.repodrivers.AasembleDriver')
    def test_native(self):
        from aasemble.django.apps.buildsvc.management.commands.import_dsc import Command as ImportDsc
        dsc_path = os.path.join(os.path.dirname(__file__), 'test_data', 'import_dsc', 'native', 'hello_1.0-1.dsc')
        ImportDsc().handle(user='brandon', repository='brandon', path=dsc_path)

        sp = SourcePackage.objects.get(name='hello')
        spv = SourcePackageVersion.objects.get(source_package=sp, version='1.0-1')
        SourcePackageVersionFile.objects.get(source_package_version=spv, file_type=SOURCE_PACKAGE_FILE_TYPE_DSC)
        SourcePackageVersionFile.objects.get(source_package_version=spv, file_type=SOURCE_PACKAGE_FILE_TYPE_NATIVE)

        sources_entry = deb822.Deb822(spv.format_for_sources())
        self.assertEquals(list(sources_entry.keys()),
                          ['Package',
                           'Binary',
                           'Version',
                           'Maintainer',
                           'Standards-Version',
                           'Architecture',
                           'Homepage',
                           'Format',
                           'Directory',
                           'Files',
                           'Checksums-Sha1',
                           'Checksums-Sha256'])
        self.assertEquals(sources_entry['Package'], 'hello')
        self.assertEquals(sources_entry['Version'], '1.0-1')
        self.assertEquals(sources_entry['Maintainer'], 'Soren Hansen <soren@aasemble.com>')
        self.assertEquals(sources_entry['Standards-Version'], '3.9.2')
        self.assertEquals(sources_entry['Architecture'], 'any')
        self.assertEquals(sources_entry['Homepage'], 'http://example.com/hello/')
        self.assertEquals(sources_entry['Format'], '3.0 (native)')
        self.assertEquals(sources_entry['Directory'], 'pool/main/h/hello')
        self.assertEquals(sources_entry['Files'], '\n baaf58ea1635765ed569231ae478350e 484 hello_1.0-1.dsc'
                                                  '\n 098b9b276c9b1da964e021b71414c998 673 hello_1.0-1.tar.gz')
        self.assertEquals(sources_entry['Checksums-Sha1'], '\n 1b946853f1eea400ad6fd25ca46a8802a40d200c 484 hello_1.0-1.dsc'
                                                           '\n 24f3bf00b0037dd216cdad785cdc07c8a7f7db62 673 hello_1.0-1.tar.gz')
        self.assertEquals(sources_entry['Checksums-Sha256'], '\n a9c5ba1e786b5d4703d99df1378152456c84399fe1eb63e293d696540965f978 484 hello_1.0-1.dsc'
                                                             '\n 7d2897859802ed68e771958655960d81d2b985fb23fc11ec129234804f22cf04 673 hello_1.0-1.tar.gz')
        self.assertTrue(os.path.exists(os.path.join(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR,
                                                    'brandon', 'brandon',
                                                    'pool/main/h/hello/hello_1.0-1.dsc')),
                        'dsc was not copied into the pool dir')
        self.assertTrue(os.path.exists(os.path.join(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR,
                                                    'brandon', 'brandon',
                                                    'pool/main/h/hello/hello_1.0-1.tar.gz')),
                        'Tarball was not copied into the pool dir')
        with open(os.path.join(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR,
                               'brandon/brandon/dists/aasemble/main/source/Sources'), 'r') as fp:
            self.assertIn(spv.format_for_sources(), fp.read())


class ImportDebTestCase(TestCase):
    @override_settings(BUILDSVC_REPODRIVER='aasemble.django.apps.buildsvc.repodrivers.AasembleDriver')
    def test_simple(self):
        from aasemble.django.apps.buildsvc.management.commands.import_deb import Command as ImportDeb
        deb_path = os.path.join(os.path.dirname(__file__), 'test_data/import_deb/pool/main/h/hello/hello_1.0-1_amd64.deb')
        ImportDeb().handle(user='brandon', repository='brandon', path=deb_path)

        bp = BinaryPackage.objects.get(name='hello')
        bpv = BinaryPackageVersion.objects.get(binary_package=bp, version='1.0-1')

        packages_entry = deb822.Deb822(bpv.format_for_packages())
        self.assertEquals(list(packages_entry.keys()),
                          ['Package',
                           'Source',
                           'Version',
                           'Architecture',
                           'Maintainer',
                           'Installed-Size',
                           'Priority',
                           'Section',
                           'Homepage',
                           'Filename',
                           'Size',
                           'MD5sum',
                           'SHA1',
                           'SHA256',
                           'Description'])
        self.assertEquals(packages_entry['Package'], 'hello')
        self.assertEquals(packages_entry['Source'], 'hello')
        self.assertEquals(packages_entry['Version'], '1.0-1')
        self.assertEquals(packages_entry['Architecture'], 'amd64')
        self.assertEquals(packages_entry['Maintainer'], 'Soren Hansen <soren@aasemble.com>')
        self.assertEquals(packages_entry['Installed-Size'], '25')
        self.assertEquals(packages_entry['Priority'], 'optional')
        self.assertEquals(packages_entry['Section'], 'misc')
        self.assertEquals(packages_entry['Homepage'], 'http://example.com/hello/')
        self.assertEquals(packages_entry['Filename'], 'pool/main/h/hello/hello_1.0-1_amd64.deb')
        self.assertEquals(packages_entry['Size'], '1070')
        self.assertEquals(packages_entry['MD5sum'], 'f2451350cde2bec3cd6b7d39b89a5270')
        self.assertEquals(packages_entry['SHA1'], '7efd808803711d5cec23424ccf805289b47d2b55')
        self.assertEquals(packages_entry['SHA256'], '1ea0262ecdca1bfdd3d6c0b4844d4a7aa6f441bd5c58e972012578ac9ba246db')
        self.assertTrue(os.path.exists(os.path.join(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR,
                                                    'brandon', 'brandon',
                                                    'pool/main/h/hello/hello_1.0-1_amd64.deb')),
                        'Deb was not copied into the pool dir')
        with open(os.path.join(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR,
                               'brandon/brandon/dists/aasemble/main/binary-amd64/Packages'), 'r') as fp:
            self.assertIn(bpv.format_for_packages(), fp.read())
