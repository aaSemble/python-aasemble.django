import mock
import operator
import os.path

from django.contrib.auth import models as auth_models
from django.test import override_settings

from aasemble.django.tests import AasembleTestCase as TestCase
from .models import Repository, Series, PackageSource

class RepositoryTestCase(TestCase):
    fixtures = ['data.json']


    def test_unicode(self):
        repo = Repository.objects.get(id=1)
        self.assertEquals(str(repo), 'sorenh/sorenh')


    def test_lookup_by_user_with_extra_admin(self):
        sorenh = auth_models.User.objects.get(id=1)
        self.assertEquals(set([1, 2, 3]), set([repo.id for repo in Repository.lookup_by_user(sorenh)]))


    def test_lookup_by_user_without_extra_admin(self):
        alterego = auth_models.User.objects.get(id=2)
        self.assertEquals(set([3]), set([repo.id for repo in Repository.lookup_by_user(alterego)]))

    def test_user_can_modify_own_repo(self):
        sorenh = auth_models.User.objects.get(id=1)
        self.assertTrue(Repository.objects.get(id=1).user_can_modify(sorenh))
        self.assertTrue(Repository.objects.get(id=2).user_can_modify(sorenh))

    def test_user_can_modify_other_repo(self):
        sorenh = auth_models.User.objects.get(id=1)
        self.assertTrue(Repository.objects.get(id=3).user_can_modify(sorenh))

    def test_user_can_not_modify_other_repo(self):
        alterego = auth_models.User.objects.get(id=2)
        self.assertFalse(Repository.objects.get(id=1).user_can_modify(alterego))

    def test_ensure_key_noop_when_key_id_set(self):
        repo = Repository.objects.get(id=1)
        with mock.patch('aasemble.django.apps.buildsvc.models.run_cmd') as run_cmd:
            repo.ensure_key()
            self.assertFalse(run_cmd.called)

    def test_ensure_key_generates_when_needed(self):
        repo = Repository.objects.get(id=2)
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


    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s:s)
    def test_basedir(self):
        repo = Repository.objects.get(id=2)
        self.assertEquals(repo.basedir, '/some/dir/sorenh/other')


    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s:s)
    def test_confdir(self):
        repo = Repository.objects.get(id=2)
        self.assertEquals(repo.confdir(), '/some/dir/sorenh/other/conf')


    @override_settings(BUILDSVC_REPOS_BASE_PUBLIC_DIR='/some/public/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s:s)
    def test_outdir(self):
        repo = Repository.objects.get(id=2)
        self.assertEquals(repo.outdir(), '/some/public/dir/sorenh/other')


    @override_settings(BUILDSVC_REPOS_BASE_PUBLIC_DIR='/some/public/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s:s)
    def test_buildlogdir(self):
        repo = Repository.objects.get(id=2)
        self.assertEquals(repo.buildlogdir, '/some/public/dir/sorenh/other/buildlogs')


    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s:s)
    def test_gpghome(self):
        repo = Repository.objects.get(id=2)
        self.assertEquals(repo.gpghome(), '/some/dir/sorenh/other/.gnupg')


    @override_settings(BUILDSVC_REPOS_BASE_DIR='/some/public/dir')
    @mock.patch('aasemble.django.apps.buildsvc.models.ensure_dir', lambda s:s)
    def test_ensure_directory_structure(self):
        with mock.patch('aasemble.django.apps.buildsvc.models.recursive_render') as recursive_render:
            repo = Repository.objects.get(id=2)
            repo.ensure_directory_structure()

            srcdir = os.path.join(os.path.dirname(__file__), 'templates', 'buildsvc', 'reprepro')
            dstdir = '/some/public/dir/sorenh/other'
            context = {'repository': repo}
            recursive_render.assert_called_with(srcdir, dstdir, context)


    def test_export(self):
        repo = Repository.objects.get(id=2)
        with mock.patch.multiple(repo, ensure_key=mock.DEFAULT,
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
        with mock.patch.multiple(repo, export=mock.DEFAULT,
                                       ensure_directory_structure=mock.DEFAULT,
                                       _reprepro=mock.DEFAULT) as mocks:

            # Ensure that ensure_directory_structure() is called and ddebs are removed before _reprepro
            mocks['_reprepro'].side_effect = lambda *args:self.assertTrue(mocks['ensure_directory_structure'].called and remove_ddebs_from_changes.called)

            # Ensure that _reprepro() is called before export
            mocks['export'].side_effect = lambda:self.assertTrue(mocks['_reprepro'].called)

            repo.process_changes('myseries', '/path/to/changes')

            remove_ddebs_from_changes.assert_called_with('/path/to/changes')
            mocks['export'].assert_called_with()
            mocks['ensure_directory_structure'].ensure_called_with()
            mocks['_reprepro'].ensure_called_with('--ignore=wrongdistribution', 'include', 'myseries', '/path/to/changes')


    @override_settings(BUILDSVC_REPOS_BASE_URL='http://example.com/some/dir')
    def test_baseurl(self):
        repo = Repository.objects.get(id=2)
        self.assertEquals(repo.base_url, 'http://example.com/some/dir/sorenh/other')


class PackageSourceTestCase(TestCase):
    fixtures = ['data.json']

    @mock.patch('aasemble.django.apps.buildsvc.tasks.reprepro')
    def test_post_delete(self, reprepro):
        ps = PackageSource.objects.create(series_id=1,
                                          git_url='https://example.com/git',
                                          branch='master',
                                          last_built_name='something')
        ps.delete()
        reprepro.delay.assert_called_with(1, 'removesrc', 'aasemble', 'something')
