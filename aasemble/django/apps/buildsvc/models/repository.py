import os.path
import uuid

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from aasemble.django.apps.buildsvc import tasks
from aasemble.django.apps.buildsvc.repodrivers import get_repo_driver
from aasemble.utils import ensure_dir


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

    def first_series(self):
        try:
            return self.series.all()[0]
        except IndexError:
            from aasemble.django.apps.buildsvc.models.series import Series
            return Series.objects.create(name=settings.BUILDSVC_DEFAULT_SERIES_NAME, repository=self)

    @property
    def outdir(self):
        outdir = os.path.join(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR,
                              self.user.username, self.name)
        return ensure_dir(outdir)

    @property
    def buildlogdir(self):
        return ensure_dir(os.path.join(self.outdir, 'buildlogs'))

    def _key_data(self):
        return get_repo_driver(self).key_data()

    def key_url(self):
        return '%s/repo.key' % (self.base_url,)

    def export(self):
        self.first_series()
        return get_repo_driver(self).export()

    def process_changes(self, series_name, changes_file):
        return get_repo_driver(self).process_changes(series_name, changes_file)

    def import_deb(self, series_name, deb_file):
        return get_repo_driver(self).import_deb(series_name, deb_file)

    def import_dsc(self, series_name, dsc_file):
        return get_repo_driver(self).import_dsc(series_name, dsc_file)

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
