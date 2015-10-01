import os.path
from urlparse import urlparse

from ...utils import run_cmd

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db import models

from django.template.loader import render_to_string

class MirrorSet(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(auth_models.User)
    mirrors = models.ManyToManyField('Mirror')


class Mirror(models.Model):
    owner = models.ForeignKey(auth_models.User)
    url = models.URLField(max_length=200)
    series = models.CharField(max_length=200)
    components = models.CharField(max_length=200)
    public = models.BooleanField(default=False)

    def __unicode__(self):
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

    def update_mirror(self):
        self.write_config()
        run_cmd(['apt-mirror', 'mirror.conf'], cwd=self.basepath)


class Architecture(models.Model):
    name = models.CharField(max_length=50)
    apt_mirror_prefix = models.CharField(max_length=20)

    def __unicode__(self):
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
            self.sync_dists()
            self.symlink_pool()
