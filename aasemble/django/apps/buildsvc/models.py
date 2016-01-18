import logging
import os
import os.path
import shutil
import tempfile
import uuid

from allauth.socialaccount.models import SocialToken

import deb822

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.contrib.sites.models import Site
from django.db import models
from django.template.loader import render_to_string
from django.utils.encoding import python_2_unicode_compatible
from django.utils.module_loading import import_string
from django.utils.timezone import now

import github3

from six.moves.urllib.parse import urlparse

from . import tasks
from ...exceptions import CommandFailed
from ...utils import ensure_dir, recursive_render, run_cmd

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
    driver_name = getattr(settings, 'BUILDSVC_REPODRIVER', 'aasemble.django.apps.buildsvc.models.RepreproDriver')
    driver = import_string(driver_name)
    return driver(repository)


@python_2_unicode_compatible
class Repository(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(auth_models.User)
    name = models.CharField(max_length=100)
    key_id = models.CharField(max_length=100)
    key_data = models.TextField(null=False)
    extra_admins = models.ManyToManyField(auth_models.Group)

    class Meta:
        verbose_name_plural = 'repositories'
        unique_together = (('user', 'name'),)

    def __str__(self):
        return '%s/%s' % (self.user.username, self.name)

    @property
    def sources(self):
        return PackageSource.objects.filter(series__repository=self)

    @classmethod
    def lookup_by_user(cls, user):
        if not user.is_active:
            return cls.objects.none()
        if user.is_superuser:
            return cls.objects.all()
        return cls.objects.filter(user=user) | cls.objects.filter(extra_admins__in=user.groups.all())

    def ensure_key(self):
        if not self.key_id:
            self.key_id = get_repo_driver(self).generate_key()
            self.save()

    def first_series(self):
        try:
            return self.series.all()[0]
        except IndexError:
            return Series.objects.create(name=settings.BUILDSVC_DEFAULT_SERIES_NAME, repository=self)

    @property
    def basedir(self):
        basedir = os.path.join(settings.BUILDSVC_REPOS_BASE_DIR, self.user.username, self.name)
        return ensure_dir(basedir)

    def confdir(self):
        confdir = os.path.join(self.basedir, 'conf')
        return ensure_dir(confdir)

    def outdir(self):
        outdir = os.path.join(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR, self.user.username, self.name)
        return ensure_dir(outdir)

    @property
    def buildlogdir(self):
        return ensure_dir(os.path.join(self.outdir(), 'buildlogs'))

    def gpghome(self):
        return os.path.join(self.basedir, '.gnupg')

    def ensure_directory_structure(self):
        recursive_render(os.path.join(os.path.dirname(__file__),
                                      'templates/buildsvc/reprepro'),
                         self.basedir, {'repository': self})

    def _reprepro(self, *args):
        env = {'GNUPG_HOME': self.gpghome()}
        return run_cmd(['reprepro', '-b', self.basedir, '--waitforlock=10'] + list(args),
                       override_env=env)

    def _key_data(self):
        return get_repo_driver(self).key_data()

    def key_url(self):
        return '%s/repo.key' % (self.base_url,)

    def export_key(self):
        keypath = os.path.join(self.outdir(), 'repo.key')
        if not os.path.exists(keypath):
            with open(keypath, 'w') as fp:
                fp.write(self.key_data)

    def export(self):
        self.first_series()
        self.ensure_key()
        self.ensure_directory_structure()
        self.export_key()
        self._reprepro('export')

    def process_changes(self, series_name, changes_file):
        self.ensure_directory_structure()
        remove_ddebs_from_changes(changes_file)
        self._reprepro('--ignore=wrongdistribution', 'include', series_name, changes_file)
        self.export()

    def save(self, *args, **kwargs):
        super(Repository, self).save(*args, **kwargs)
        tasks.export.delay(self.id)

    @property
    def base_url(self):
        return '%s/%s/%s' % (settings.BUILDSVC_REPOS_BASE_URL,
                             self.user.username,
                             self.name)

    def user_can_modify(self, user):
        if not user.is_active:
            return False
        if user == self.user or user.is_superuser:
            return True
        if self.extra_admins.filter(user=user).exists():
            return True
        return False


@python_2_unicode_compatible
class Series(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    repository = models.ForeignKey(Repository, related_name='series')

    def __str__(self):
        return '%s/%s' % (self.repository.name, self.name)

    def binary_source_list(self, force_trusted=False):
        return self._source_list(prefix='deb', force_trusted=force_trusted)

    def source_source_list(self, force_trusted=False):
        return self._source_list(prefix='deb-src', force_trusted=force_trusted)

    def _source_list(self, prefix, force_trusted=False):
        if force_trusted:
            option = ' [trusted=yes]'
        else:
            option = ''
        return '%s%s %s %s main' % (prefix,
                                    option,
                                    self.repository.base_url,
                                    self.name)

    class Meta:
        verbose_name_plural = 'series'

    def process_changes(self, changes_file):
        self.repository.process_changes(self.name, changes_file)

    def build_sources_list(self):
        sources = []
        for series in ('trusty', 'trusty-updates', 'trusty-security'):
            sources += ['deb http://archive.ubuntu.com/ubuntu {} main universe restricted multiverse'.format(series)]
        sources += [self.binary_source_list(force_trusted=True)]
        sources += sum([extdep.deb_lines for extdep in self.externaldependency_set.all()], [])
        return '\n'.join(sources)

    def build_apt_keys(self):
        keys = [self.repository.key_data]
        keys += [extdep.key for extdep in self.externaldependency_set.all()]
        return '\n'.join(keys)

    def export(self):
        self.repository.export()

    def user_can_modify(self, user):
        return self.repository.user_can_modify(user)


class ExternalDependency(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    url = models.URLField()
    series = models.CharField(max_length=200)
    components = models.CharField(max_length=200, null=True, blank=True)
    own_series = models.ForeignKey(Series)
    key = models.TextField()

    @property
    def deb_line(self):
        return '\n'.join(self.deb_lines)

    @property
    def deb_lines(self):
        return ['deb %s %s %s' % (self.url, series, self.components) for series in self.series.split(' ')]

    def user_can_modify(self, user):
        return self.own_series.user_can_modify(user)

    @classmethod
    def lookup_by_user(cls, user):
        if not user.is_active:
            return cls.objects.none()
        if user.is_superuser:
            return cls.objects.all()
        return cls.objects.filter(own_series__repository__user=user) | cls.objects.filter(own_series__repository__extra_admins__in=user.groups.all())


class NotAValidGithubRepository(Exception):
    pass


@python_2_unicode_compatible
class PackageSource(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    git_url = models.URLField()
    branch = models.CharField(max_length=100)
    series = models.ForeignKey(Series, related_name='sources')
    last_seen_revision = models.CharField(max_length=64, null=True, blank=True)
    last_built_version = models.CharField(max_length=64, null=True, blank=True)
    last_built_name = models.CharField(max_length=64, null=True, blank=True)
    build_counter = models.IntegerField(default=0)
    webhook_registered = models.BooleanField(default=False)
    last_failure_time = models.DateTimeField(null=True, blank=True)
    last_failure = models.CharField(max_length=255, null=True, blank=True)
    disabled = models.BooleanField(default=False)

    def __str__(self):
        return '%s/%s' % (self.git_url, self.branch)

    @property
    def repository(self):
        return self.series.repository

    def poll(self):
        cmd = ['git', 'ls-remote', self.git_url,
               'refs/heads/%s' % self.branch]
        try:
            stdout = run_cmd(cmd)
            stdout = stdout.decode()
        except CommandFailed as e:
            self.last_failure_time = now()
            self.last_failure = e.stdout
            self.disabled = True
            self.save()
            return False

        sha = stdout.split('\t')[0]

        if sha == self.last_seen_revision:
            return False

        self.last_seen_revision = sha
        self.save()
        return True

    def checkout(self, sha=None, logger=LOG):
        tmpdir = tempfile.mkdtemp()
        builddir = os.path.join(tmpdir, 'build')
        try:
            run_cmd(['git',
                     'clone', self.git_url,
                     '--recursive',
                     '-b', self.branch,
                     'build'],
                    cwd=tmpdir, logger=logger)

            if sha:
                run_cmd(['git', 'reset', '--hard', sha], cwd=builddir, logger=logger)

            stdout = run_cmd(['git', 'rev-parse', 'HEAD'], cwd=builddir, logger=logger)
            return tmpdir, builddir, stdout.strip()
        except:
            shutil.rmtree(tmpdir)
            raise

    @property
    def long_name(self):
        return '_'.join(filter(bool, urlparse(self.git_url).path.split('/')))

    @property
    def name(self):
        return self.git_url.split('/')[-1].replace('_', '-')

    def build(self):
        tasks.build.delay(self.id)

    def build_real(self):
        self.build_counter += 1
        self.save()

        br = BuildRecord(source=self, build_counter=self.build_counter)
        br.save()

        tmpdir, self.builddir, br.sha = self.checkout(logger=br.logger)
        br.save()
        try:
            site = Site.objects.get_current()
            br_url = '%s://%s%s' % (getattr(settings, 'AASEMBLE_DEFAULT_PROTOCOL', 'http'),
                                    site.domain, br.get_absolute_url())

            version = run_cmd(['aasemble-pkgbuild', 'version', br_url], cwd=self.tmpdir, logger=br.logger)
            name = run_cmd(['aasemble-pkgbuild', 'name', br_url], cwd=self.tmpdir, logger=br.logger)

            br.version = version
            br.save()

            self.last_built_version = version
            self.last_built_name = name
            self.save()

            run_cmd(['aasemble-pkgbuild', 'build', br_url], cwd=self.tmpdir, logger=br.logger)
            br.build_finished = now()
            br.build_record.save()

            changes_files = filter(lambda s: s.endswith('.changes'), os.listdir(tmpdir))

            for changes_file in changes_files:
                self.series.process_changes(os.path.join(tmpdir, changes_file))

            self.series.export()
        finally:
            shutil.rmtree(tmpdir)

    def delete_on_filesystem(self):
        if self.last_built_name:
            tasks.reprepro.delay(self.series.repository.id, 'removesrc', self.series.name, self.last_built_name)

    def user_can_modify(self, user):
        return self.series.user_can_modify(user)

    def github_owner_repo(self):
        github_prefix = 'https://github.com/'

        if not self.git_url.startswith(github_prefix):
            raise NotAValidGithubRepository()

        owner_repo = self.git_url[len(github_prefix):]

        parts = owner_repo.split('/')

        if len(parts) != 2:
            raise NotAValidGithubRepository()

        if parts[1].endswith('.git'):
            parts[1] = parts[1][:-4]

        return (parts[0], parts[1])

    def register_webhook(self):
        if not getattr(settings, 'AASEMBLE_BUILDSVC_USE_WEBHOOKS', True):
            return True

        if self.webhook_registered:
            return True

        try:
            owner, repo = self.github_owner_repo()
        except NotAValidGithubRepository:
            return False

        try:
            for token in SocialToken.objects.filter(account__in=self.series.repository.user.socialaccount_set.filter(provider='github')):
                gh = github3.GitHub(token=token.token)
                repo = gh.repository(owner, repo)
                if repo.create_hook(name='web', config={'url': settings.GITHUB_WEBHOOK_URL,
                                                        'content_type': 'json'}):
                    self.webhook_registered = True
                    self.save()
                    return True
        except github3.GitHubError as exc:
            msgs = [e['message'] for e in exc.errors]
            if 'Hook already exists on this repository' in msgs:
                self.webhook_registered = True
                self.save()
            else:
                raise

        return False


class BuildRecord(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(PackageSource)
    version = models.CharField(max_length=50)
    build_counter = models.IntegerField(default=0)
    build_started = models.DateTimeField(auto_now_add=True)
    build_finished = models.DateTimeField(blank=True, null=True)
    sha = models.CharField(max_length=100, null=True, blank=True)

    def __init__(self, *args, **kwargs):
        self._logger = None
        self._saved_logpath = None
        return super(BuildRecord, self).__init__(*args, **kwargs)

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('v3_buildrecord-detail', args=[str(self.uuid)])

    @property
    def logger(self):
        logpath = self.buildlog()

        if not logpath == self._saved_logpath:
            LOG.debug('logpath changed from %r to %r' % (self._saved_logpath, logpath))

            # buildlog path changed, move it
            if self._saved_logpath and os.path.exists(self._saved_logpath):
                LOG.debug('Existing logfile found. Renaming')
                os.rename(self._saved_logpath, self.buildlog())

            logger = logging.getLogger('buildsvc.pkgbuild.%s_%s' % (self.source.name, self.build_counter))
            logger.setLevel(logging.DEBUG)

            for handler in logger.handlers:
                logger.removeHandler(handler)

            formatter = logging.Formatter('%(asctime)s: %(message)s')
            logfp = logging.FileHandler(logpath)
            logfp.setLevel(logging.DEBUG)
            logfp.setFormatter(formatter)

            logger.addHandler(logfp)
            self._logger = logger
            self._saved_logpath = logpath

        return self._logger

    def logpath(self):
        LOG.debug('Determining logpath for %s. version = %r' % (self, self.version))
        if self.version:
            return os.path.join(self.source.long_name, '%s_%s.log' % (self.source.long_name, self.version))
        else:
            return os.path.join(self.source.long_name, '%s_%s.tmp.log' % (self.source.long_name, self.build_counter))

    def buildlog(self):
        path = os.path.join(self.source.series.repository.buildlogdir,
                            self.logpath())

        dirpath = os.path.dirname(path)

        if not os.path.isdir(dirpath):
            os.makedirs(dirpath)

        return path

    def buildlog_url(self):
        return '%s/buildlogs/%s' % (self.source.series.repository.base_url, self.logpath())

    @property
    def duration(self):
        if self.build_started and self.build_finished:
            return (self.build_finished - self.build_started).total_seconds()


@python_2_unicode_compatible
class GithubRepository(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(auth_models.User)
    repo_owner = models.CharField(max_length=100)
    repo_name = models.CharField(max_length=100)

    def __str__(self):
        return self.url

    class Meta:
        verbose_name_plural = 'Github repositories'
        ordering = ['repo_owner', 'repo_name']
        unique_together = ('user', 'repo_owner', 'repo_name')

    @property
    def url(self):
        return 'https://github.com/%s/%s' % (self.repo_owner, self.repo_name)

    @classmethod
    def create_from_github_repo(cls, user, github_repo):
        obj = cls(user=user,
                  repo_owner=github_repo['owner']['login'],
                  repo_name=github_repo['name'])
        obj.save()
        return obj
