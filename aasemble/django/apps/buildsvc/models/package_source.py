import logging
import os.path
import uuid

from allauth.socialaccount.models import SocialToken

from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now

import github3

from six.moves.urllib.parse import urlparse

from aasemble.django.apps.buildsvc import executors, tasks
from aasemble.utils import TemporaryDirectory, run_cmd
from aasemble.utils.exceptions import CommandFailed

LOG = logging.getLogger(__name__)


class NotAValidGithubRepository(Exception):
    pass


@python_2_unicode_compatible
class PackageSource(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    git_url = models.URLField()
    branch = models.CharField(max_length=100)
    series = models.ForeignKey('Series', related_name='sources')
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

    @property
    def long_name(self):
        return '_'.join(filter(bool, urlparse(self.git_url).path.split('/')))

    @property
    def name(self):
        return self.git_url.split('/')[-1].replace('_', '-')

    def build(self):
        tasks.build.delay(self.id)

    def build_real(self):
        timestamp = now().strftime('%s%f')
        with executors.get_executor('b-%s-%s' % (self.uuid, timestamp)) as executor, TemporaryDirectory() as tmpdir:
            with self.create_build() as b:
                b.run(tmpdir, executor)

            executor.get('*.*', tmpdir)

            changes_files = filter(lambda s: s.endswith('.changes'), os.listdir(tmpdir))
            for changes_file in changes_files:
                self.series.process_changes(os.path.join(tmpdir, changes_file))

            dsc_files = filter(lambda s: s.endswith('.dsc'), os.listdir(tmpdir))
            for dsc_file in dsc_files:
                self.series.import_dsc(dsc_file)

            deb_files = filter(lambda s: s.endswith('.deb'), os.listdir(tmpdir))
            for deb_file in deb_files:
                self.series.import_deb(dsc_file)

            self.series.export()

    def increment_build_counter(self):
        with transaction.atomic():
            self.build_counter = F('build_counter') + 1
            self.save()
            self.refresh_from_db()

    def create_build(self):
        self.increment_build_counter()

        from aasemble.django.apps.buildsvc.models.build import Build
        return Build.objects.create(source=self,
                                    build_counter=self.build_counter,
                                    sha=self.last_seen_revision)

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
