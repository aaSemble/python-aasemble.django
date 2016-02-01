import os.path
import uuid

import deb822

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from aasemble.django.apps.buildsvc import tasks
from aasemble.django.apps.buildsvc.repodrivers import get_repo_driver
from aasemble.django.utils import ensure_dir, recursive_render, run_cmd


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
        from aasemble.django.apps.buildsvc.models.package_source import PackageSource
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
        if not self.key_data:
            self.key_data = self._key_data()
            self.save()

    def first_series(self):
        try:
            return self.series.all()[0]
        except IndexError:
            from aasemble.django.apps.buildsvc.models.series import Series
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
        tmpl_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   '..', 'templates/buildsvc/reprepro'))
        recursive_render(tmpl_dir, self.basedir, {'repository': self})

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
