import os.path
from six.moves.urllib.parse import urlparse

from ...utils import run_cmd

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db import models
from django.template.loader import render_to_string
from django.utils.encoding import python_2_unicode_compatible

from . import tasks

class MirrorSet(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(auth_models.User)
    mirrors = models.ManyToManyField('Mirror')
    extra_admins = models.ManyToManyField(auth_models.Group)

    @classmethod
    def lookup_by_user(cls, user):
        if not user.is_active:
            return cls.objects.none()
        if user.is_superuser:
            return cls.objects.all()
        return cls.objects.filter(owner=user) | cls.objects.filter(extra_admins=user.groups.all())


@python_2_unicode_compatible
class Mirror(models.Model):
    owner = models.ForeignKey(auth_models.User)
    url = models.URLField(max_length=200)
    series = models.CharField(max_length=200)
    components = models.CharField(max_length=200)
    public = models.BooleanField(default=False)
    refresh_in_progress = models.BooleanField(default=False)
    extra_admins = models.ManyToManyField(auth_models.Group)

    def __str__(self):
        return '<Mirror of %s (owner=%s)' % (self.url, self.owner)

    def series_list(self):
        return self.series.split(' ')

    def get_config(self):
        return render_to_string('buildsvc/apt-mirror.conf',
                                {'mirror': self})

    def write_config(self):
        with open('%s/mirror.conf' % (self.basepath,), 'w') as fp:
            fp.write(self.get_config())

    @property
    def basepath(self):
        d = os.path.join(settings.MIRRORSVC_BASE_PATH, 'mirrors', str(self.id))
        if not os.path.isdir(d):
            os.makedirs(d)
        return d

    @property
    def archive_dir(self):
        return os.path.join(self.basepath, self.archive_subpath)

    @property
    def archive_subpath(self):
        parsed_url = urlparse(self.url)
        return os.path.join(parsed_url.netloc, parsed_url.path[1:])

    @property
    def dists(self):
        return os.path.join(self.archive_dir, 'dists')

    @property
    def pool(self):
        return os.path.join(self.archive_dir, 'pool')

    @classmethod
    def lookup_by_user(cls, user):
        if not user.is_active:
            return cls.objects.none()
        if user.is_superuser:
            return cls.objects.all()
        return cls.objects.filter(owner=user) | cls.objects.filter(extra_admins=user.groups.all())

    def schedule_update_mirror(self):
        if Mirror.objects.filter(id=self.id, refresh_in_progress=False).update(refresh_in_progress=True) > 0:
           tasks.refresh_mirror.delay(self.id)
           return True
        else:
           # Update already scheduled
           return False

    def update_mirror(self):
        self.write_config()
        try:
            run_cmd(['apt-mirror', 'mirror.conf'], cwd=self.basepath)
        finally:
            Mirror.objects.filter(id=self.id).update(refresh_in_progress=False)

    def user_can_modify(self, user):
        return user == self.owner

@python_2_unicode_compatible
class Architecture(models.Model):
    name = models.CharField(max_length=50)
    apt_mirror_prefix = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Snapshot(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    mirrorset = models.ForeignKey(MirrorSet)

    @property
    def basepath(self):
        d = os.path.join(settings.MIRRORSVC_BASE_PATH, 'snapshots', str(self.id))
        if not os.path.isdir(d):
            os.makedirs(d)
        return d

    def sync_dists(self):
        for mirror in self.mirrorset.mirrors.all():
            destdir = os.path.join(self.basepath, mirror.archive_subpath)
            if not os.path.exists(destdir):
                os.makedirs(destdir)
            run_cmd(['rsync', '-aHAPvi', '--exclude=**/i18n', mirror.dists, destdir])


    def symlink_pool(self):
        for mirror in self.mirrorset.mirrors.all():
            destdir = os.path.join(self.basepath, mirror.archive_subpath, 'pool')
            if not os.path.exists(destdir):
                os.symlink(mirror.pool, destdir)

    def save(self, *args, **kwargs):
        perform_snapshot = False

        if self.pk is None:
            perform_snapshot = True

        rv = super(Snapshot, self).save(*args, **kwargs)

        if perform_snapshot:
            tasks.perform_snapshot.delay(self.id)

    def perform_snapshot(self):
        self.sync_dists()
        self.symlink_pool()
