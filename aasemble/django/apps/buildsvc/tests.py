import os.path
import subprocess
import time

from django.contrib.auth import models as auth_models
from django.db.utils import IntegrityError
from django.test import override_settings
from django.test.utils import skipIf

import github3

import mock

from aasemble.django.tests import AasembleTestCase as TestCase

from .models import BuildRecord, NotAValidGithubRepository, PackageSource, Repository, Series

try:
    subprocess.check_call(['docker', 'ps'])
    docker_available = True
except:
    docker_available = False


class PkgBuildTestCase(TestCase):
    @skipIf(not docker_available, 'Docker unavailable')
    def test_build_debian(self):
        import pkgbuild

        basedir = os.path.join(os.path.dirname(__file__), 'test_data', 'debian')
        builddir = os.path.join(basedir, 'build')

        builder_cls = pkgbuild.choose_builder(builddir)
        self.assertEquals(builder_cls, pkgbuild.debian.DebianBuilder)

        start = time.time()

        source = PackageSource.objects.get(id=1)
        br = BuildRecord(source=source, build_counter=10, sha='e65b55054c5220321c56bb3dfa96fbe5199f329c')
        br.save()

        builder = builder_cls(basedir, source, br)
        builder.build()

        finish = time.time()

        our_timing = finish - start
        br_timing = (br.build_finished - br.build_started).total_seconds()

        self.assertGreater(our_timing, br_timing,
                           'Our timing was smaller than measured in the build record')

        self.assertLess(our_timing - br_timing, 5,
                        'Our timing differed by more than 5 seconds from that in the build record')

        self.assertTrue(os.path.exists(os.path.join(basedir, 'buildsvctest_0.1+10_source.changes')))
        self.assertTrue(os.path.exists(os.path.join(basedir, 'buildsvctest_0.1+10_amd64.changes')))


class RepositoryTestCase(TestCase):
    def test_unicode(self):
        repo = Repository.objects.get(id=12)
        self.assertEquals(str(repo), 'eric/eric5')

    def test_lookup_by_user_with_extra_admin(self):
        charles = auth_models.User.objects.get(id=3)
        self.assertEquals(set([2, 3]), set([repo.id for repo in Repository.lookup_by_user(charles)]))

    def test_lookup_by_user_without_extra_admin(self):
        frank = auth_models.User.objects.get(id=4)
        self.assertEquals(set([3]), set([repo.id for repo in Repository.lookup_by_user(frank)]))

    def test_lookup_by_user_with_multiple_groups(self):
        brandon = auth_models.User.objects.get(id=2)
        self.assertEquals(set([1, 3]), set([repo.id for repo in Repository.lookup_by_user(brandon)]))

    def test_user_can_modify_own_repo(self):
        eric = auth_models.User.objects.get(id=5)
        self.assertTrue(Repository.objects.get(id=4).user_can_modify(eric))
        self.assertTrue(Repository.objects.get(id=12).user_can_modify(eric))

    def test_user_can_modify_other_repo(self):
        charles = auth_models.User.objects.get(id=3)
        self.assertTrue(Repository.objects.get(id=3).user_can_modify(charles))

    def test_user_can_not_modify_other_repo(self):
        brandon = auth_models.User.objects.get(id=2)
        self.assertFalse(Repository.objects.get(id=12).user_can_modify(brandon))

    def test_ensure_key_noop_when_key_id_set(self):
        repo = Repository.objects.get(id=1)
        with mock.patch('aasemble.django.apps.buildsvc.models.run_cmd') as run_cmd:
            repo.ensure_key()
            self.assertFalse(run_cmd.called)

    def test_ensure_key_generates_when_needed(self):
        repo = Repository.objects.get(id=13)
        repo.ensure_key()
        self.assertEquals(repo.key_id, 'FAKEID')

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

    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s: s)
    def test_basedir(self):
        repo = Repository.objects.get(id=12)
        self.assertEquals(repo.basedir, '/some/dir/eric/eric5')

    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s: s)
    def test_confdir(self):
        repo = Repository.objects.get(id=12)
        self.assertEquals(repo.confdir(), '/some/dir/eric/eric5/conf')

    @override_settings(BUILDSVC_REPOS_BASE_PUBLIC_DIR='/some/public/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s: s)
    def test_outdir(self):
        repo = Repository.objects.get(id=12)
        self.assertEquals(repo.outdir(), '/some/public/dir/eric/eric5')

    @override_settings(BUILDSVC_REPOS_BASE_PUBLIC_DIR='/some/public/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s: s)
    def test_buildlogdir(self):
        repo = Repository.objects.get(id=12)
        self.assertEquals(repo.buildlogdir, '/some/public/dir/eric/eric5/buildlogs')

    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s: s)
    def test_gpghome(self):
        repo = Repository.objects.get(id=12)
        self.assertEquals(repo.gpghome(), '/some/dir/eric/eric5/.gnupg')

    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/public/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s: s)
    def test_ensure_directory_structure(self):
        with mock.patch('aasemble.django.apps.buildsvc.models.recursive_render') as recursive_render:
            repo = Repository.objects.get(id=12)
            repo.ensure_directory_structure()

            srcdir = os.path.join(os.path.dirname(__file__), 'templates', 'buildsvc', 'reprepro')
            dstdir = '/some/public/dir/eric/eric5'
            context = {'repository': repo}
            recursive_render.assert_called_with(srcdir, dstdir, context)

    def test_export(self):
        repo = Repository.objects.get(id=2)
        with mock.patch.multiple(repo,
                                 ensure_key=mock.DEFAULT,
                                 ensure_directory_structure=mock.DEFAULT,
                                 export_key=mock.DEFAULT,
                                 _reprepro=mock.DEFAULT) as mocks:
            repo.export()

            mocks['ensure_key'].ensure_called_with()
            mocks['ensure_directory_structure'].ensure_called_with()
            mocks['export_key'].ensure_called_with()
            mocks['_reprepro'].ensure_called_with('export')

    @mock.patch('aasemble.django.apps.buildsvc.models.remove_ddebs_from_changes')
    def test_process_changes(self, remove_ddebs_from_changes):
        repo = Repository.objects.get(id=2)
        with mock.patch.multiple(repo,
                                 export=mock.DEFAULT,
                                 ensure_directory_structure=mock.DEFAULT,
                                 _reprepro=mock.DEFAULT) as mocks:

            # Ensure that ensure_directory_structure() is called and ddebs are removed before _reprepro
            mocks['_reprepro'].side_effect = lambda *args: self.assertTrue(mocks['ensure_directory_structure'].called and remove_ddebs_from_changes.called)

            # Ensure that _reprepro() is called before export
            mocks['export'].side_effect = lambda: self.assertTrue(mocks['_reprepro'].called)

            repo.process_changes('myseries', '/path/to/changes')

            remove_ddebs_from_changes.assert_called_with('/path/to/changes')
            mocks['export'].assert_called_with()
            mocks['ensure_directory_structure'].ensure_called_with()
            mocks['_reprepro'].ensure_called_with('--ignore=wrongdistribution', 'include', 'myseries', '/path/to/changes')

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
    @override_settings(GITHUB_WEBHOOK_URL='https://example.com/api/github/')
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
