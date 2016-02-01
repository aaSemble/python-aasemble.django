import logging
import os.path
import shutil
import tempfile
import uuid

from allauth.socialaccount.models import SocialToken

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now

import github3

from six.moves.urllib.parse import urlparse

from aasemble.django.apps.buildsvc import executors, tasks
from aasemble.django.apps.buildsvc.models.series import Series
from aasemble.django.exceptions import CommandFailed
from aasemble.django.utils import run_cmd

LOG = logging.getLogger(__name__)


def get_build_cmd(br_url, settings=settings):
    build_cmd = ['aasemble-pkgbuild']

    if hasattr(settings, 'AASEMBLE_BUILDSVC_BUILDER_HTTP_PROXY'):
        if settings.AASEMBLE_BUILDSVC_BUILDER_HTTP_PROXY:
            build_cmd += ['--proxy', settings.AASEMBLE_BUILDSVC_BUILDER_HTTP_PROXY]

    build_cmd += ['--fullname', settings.BUILDSVC_DEBFULLNAME]
    build_cmd += ['--email', settings.BUILDSVC_DEBEMAIL]
    build_cmd += ['--parallel', str(getattr(settings, 'AASEMBLE_BUILDSVC_DEFAULT_PARALLEL', 1))]

    build_cmd += ['build', br_url]
    return build_cmd


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
        from aasemble.django.apps.buildsvc.models.build_record import BuildRecord
        self.build_counter += 1
        self.save()

        br = BuildRecord(source=self, build_counter=self.build_counter,
                         sha=self.last_seen_revision)
        br.save()

        try:
            executor_class = executors.get_executor()

            with executor_class('br-%s' % (br.uuid,)) as executor:
                br.state = BuildRecord.BUILDING
                br.save()

                executor.run_cmd(['timeout', '500', 'bash', '-c', 'while ! aasemble-pkgbuild --help; do sleep 20; done'], logger=br.logger)
                tmpdir = tempfile.mkdtemp()
                try:
                    site = Site.objects.get_current()
                    br_url = '%s://%s%s' % (getattr(settings, 'AASEMBLE_DEFAULT_PROTOCOL', 'http'),
                                            site.domain, br.get_absolute_url())

                    executor.run_cmd(['aasemble-pkgbuild', 'checkout', br_url], cwd=tmpdir, logger=br.logger)
                    version = executor.run_cmd(['aasemble-pkgbuild', 'version', br_url], cwd=tmpdir, logger=br.logger)
                    name = executor.run_cmd(['aasemble-pkgbuild', 'name', br_url], cwd=tmpdir, logger=br.logger)

                    br.version = version
                    br.save()

                    self.last_built_version = version
                    self.last_built_name = name
                    self.save()

                    build_cmd = get_build_cmd(br_url)

                    executor.run_cmd(build_cmd, cwd=tmpdir, logger=br.logger)
                    br.state = br.SUCCESFULLY_BUILT
                    br.save()

                    executor.get('*.*', tmpdir)

                    br.build_finished = now()
                    br.save()

                    changes_files = filter(lambda s: s.endswith('.changes'), os.listdir(tmpdir))

                    for changes_file in changes_files:
                        self.series.process_changes(os.path.join(tmpdir, changes_file))

                    self.series.export()
                finally:
                    shutil.rmtree(tmpdir)
        finally:
            if not br.build_finished:
                br.build_finished = now()
                br.state = BuildRecord.FAILED_TO_BUILD
                br.save()

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
