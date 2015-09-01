from glob import glob
import logging
import os
import os.path
import shutil
import subprocess
import tempfile

from django.conf import settings
from django.db import models
from django.forms import ModelForm
from django.contrib.auth import models as auth_models
from django.template.loader import render_to_string

from utils import run_cmd, recursive_render

import tasks

def ensure_dir(d):
    if not os.path.isdir(d):
        os.makedirs(d)
    return d

class Repository(models.Model):
    user = models.ForeignKey(auth_models.User)
    name = models.CharField(max_length=100)
    key_id = models.CharField(max_length=100)
    extra_admins = models.ManyToManyField(auth_models.Group)
    
    class Meta:
        verbose_name_plural = 'repositories'

    def __unicode__(self):
        return '%s/%s' % (self.user.username, self.name)

    @classmethod
    def lookup_by_user(cls, user):
        return cls.objects.filter(user=user) | cls.objects.filter(extra_admins=user.groups.all())

    def ensure_key(self):
        if not self.key_id:
            gpg_input = render_to_string('buildsvc/gpg-keygen-input.tmpl',
                                         {'repository': self})
            output = run_cmd(['gpg', '--batch', '--gen-key'],input=gpg_input)

            for l in output.split('\n'):
                if l.startswith('gpg: key '):
                    self.key_id = l.split(' ')[2]
                    self.save()

    def first_series(self):
        return self.series_set.all()[0:1].get()

    @property
    def basedir(self):
        basedir = os.path.join(settings.BUILDSVC_REPOS_BASE_DIR, self.user.username, self.name)
        if not os.path.isdir(basedir):
            os.makedirs(basedir)
        return basedir

    def confdir(self):
        return os.path.join(self.basedir, 'conf')

    def outdir(self):
        return os.path.join(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR,
                            self.user.username, self.name)

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
        return run_cmd(['reprepro', '-b', self.basedir] + list(args),
                       override_env=env)

    def export(self):
        self.ensure_key()
        self.ensure_directory_structure()
        self._reprepro('export')
        
    def save(self, *args, **kwargs):
        retval = super(Repository, self).save(*args, **kwargs)

    def process_changes(self, series_name, changes_file):
        self.ensure_directory_structure()
        self._reprepro('--ignore=wrongdistribution', 'include', series_name, changes_file)
        self.export()

    @property
    def base_url(self):
        return '%s/%s/%s' % (settings.BUILDSVC_REPOS_BASE_URL,
                             self.user.username,
                             self.name)


    def user_can_modify(self, user):
        if user == self.user:
            return True
        if self.extra_admins.filter(user=user).exists():
            return True
        return False

class Series(models.Model):
    name = models.CharField(max_length=100)
    repository = models.ForeignKey(Repository)
    
    def __unicode__(self):
        return '%s/%s' % (self.repository.name, self.name)

    def binary_source_list(self):
        return self._source_list(prefix='deb')

    def source_source_list(self):
        return self._source_list(prefix='deb-src')

    def _source_list(self, prefix):
        return '%s %s %s main' % (prefix,
                                        self.repository.base_url,
                                        self.name)

    class Meta:
        verbose_name_plural = 'series'
    
    def process_changes(self, changes_file):
        self.repository.process_changes(self.name, changes_file)

    def export(self):
        self.repository.export()

    def user_can_modify(self, user):
        return self.repository.user_can_modify(user)


class PackageSource(models.Model):
    github_repository = models.ForeignKey("GithubRepository")
    branch = models.CharField(max_length=100)
    series = models.ForeignKey(Series)
    last_seen_revision = models.CharField(max_length=64, null=True, blank=True)
    last_built_version = models.CharField(max_length=64, null=True, blank=True)
    build_counter = models.IntegerField(default=0)

    def __unicode__(self):
        return '%s/%s' % (self.github_repository, self.branch)

    @property
    def url(self):
        return self.github_repository.url

    def poll(self):
        cmd = ['git', 'ls-remote', self.github_repository.url,
               'refs/heads/%s' % self.branch]
        stdout = run_cmd(cmd)
        sha = stdout.split('\t')[0]

        if sha == self.last_seen_revision:
            return False

        self.last_seen_revision = sha
        self.save()
        return True

    def checkout(self, sha=None):
        tmpdir = tempfile.mkdtemp()
        builddir = os.path.join(tmpdir, 'build')
        try:
            run_cmd(['git',
                     'clone', self.github_repository.url,
                     '-b', self.branch,
                     'build'],
                    cwd=tmpdir)

            if sha:
                run_cmd(['git', 'reset', '--hard', sha], cwd=builddir)

            stdout = run_cmd(['git', 'rev-parse', 'HEAD'], cwd=builddir)
            return tmpdir, builddir, stdout.strip()
        except:
            shutil.rmtree(tmpdir)
            raise

    @property
    def name(self):
        return self.url.split('/')[-1].replace('_', '-')
        
    def build(self):
        tasks.build.delay(self.id)

    def build_real(self):
        tmpdir, self.builddir, sha = self.checkout()
        try:
            self.build_counter += 1
            self.save()

            import pkgbuild
            builder_cls = pkgbuild.choose_builder(self.builddir)
            builder = builder_cls(tmpdir, self, self.build_counter)
            
            builder.build()

            changes_files = filter(lambda s:s.endswith('.changes'), os.listdir(tmpdir))

            for changes_file in changes_files:
                self.series.process_changes(os.path.join(tmpdir, changes_file))

            self.series.export()
        finally:
            shutil.rmtree(tmpdir)

    def user_can_modify(self, user):
        return self.repository.user_can_modify(user)


class BuildRecord(models.Model):
    source = models.ForeignKey(PackageSource)
    version = models.CharField(max_length=50)

    def __init__(self, *args, **kwargs):
        self._logger = None
        return super(BuildRecord, self).__init__(*args, **kwargs)

    @property
    def logger(self):
        if not self._logger:
            logger = logging.getLogger('%s_%s' % (self.source.name, self.version))
            logger.setLevel(logging.DEBUG)

            formatter = logging.Formatter('%(asctime)s: %(message)s')
            logfp = logging.FileHandler(self.buildlog())
            logfp.setLevel(logging.DEBUG)
            logfp.setFormatter(formatter)

            logger.addHandler(logfp)
            self._logger = logger

        return self._logger

    def buildlog(self):
        return os.path.join(self.source.series.repository.buildlogdir,
                            '%s_%s.log' % (self.source.name, self.version))

    def buildlog_url(self):
        return '%s/buildlogs/%s_%s.log' % (self.source.series.repository.base_url,
                                           self.source.name, self.version)

class GithubRepository(models.Model):
    user = models.ForeignKey(auth_models.User)
    repo_owner = models.CharField(max_length=100)
    repo_name = models.CharField(max_length=100)

    def __unicode__(self):
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


class PackageSourceForm(ModelForm):
    class Meta:
        model = PackageSource
        fields = ['github_repository', 'branch', 'series']
