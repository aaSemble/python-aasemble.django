import logging
import os.path
import uuid

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.core.urlresolvers import reverse
from django.db import models
from django.template.loader import render_to_string
from django.utils.encoding import python_2_unicode_compatible

from six.moves.urllib.parse import urlparse

from . import tasks
from ...utils import ensure_dir, run_cmd

LOG = logging.getLogger(__name__)


class MirrorSet(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
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

    @property
    def snapshots_url(self):
        # print(self.uuid)
        str_uuid = str(self.uuid)
        return reverse('mirrorsvc:mirrorset_snapshots', kwargs={'uuid': str_uuid})

    @property
    def sources_list(self):
        return '\n'.join([mirror.sources_list for mirror in self.mirrors.all()])

    def user_can_modify(self, user):
        return user == self.owner


@python_2_unicode_compatible
class Mirror(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(auth_models.User)
    url = models.URLField(max_length=200)
    series = models.CharField(max_length=200)
    components = models.CharField(max_length=200)
    public = models.BooleanField(default=False)
    refresh_in_progress = models.BooleanField(default=False)
    extra_admins = models.ManyToManyField(auth_models.Group)
    visible_to_v1_api = models.BooleanField(default=False)

    def __str__(self):
        return '<Mirror of %s (owner=%s)>' % (self.url, self.owner)

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
        d = os.path.join(settings.MIRRORSVC_BASE_PATH, 'mirrors', str(self.uuid))
        if not os.path.isdir(d):
            os.makedirs(d)
            if self.visible_to_v1_api:
                os.symlink(d, os.path.join(settings.MIRRORSVC_BASE_PATH, 'mirrors', str(self.id)))
        return d

    @property
    def archive_dir(self):
        return ensure_dir(os.path.join(self.basepath, self.archive_subpath))

    @property
    def archive_subpath(self):
        parsed_url = urlparse(self.url)
        return os.path.join(parsed_url.netloc, parsed_url.path[1:])

    @property
    def sources_list(self):
        rv = ''
        parsed_url = urlparse(self.url)
        url = '%s/%s/%s%s' % (settings.MIRRORSVC_BASE_URL, self.uuid, parsed_url.netloc, parsed_url.path)
        for series in self.series_list():
            rv += 'deb %s %s %s\n' % (url, series, self.components)
            rv += 'deb-src %s %s %s\n' % (url, series, self.components)
        return rv

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
            run_cmd(['apt-mirror', 'mirror.conf'], cwd=self.basepath, logger=self.logger)
        finally:
            Mirror.objects.filter(id=self.id).update(refresh_in_progress=False)

    def user_can_modify(self, user):
        return user == self.owner

    @property
    def logger(self):
        logpath = self.logpath()

        logger = logging.getLogger('mirrorsvc.update_mirror.%s' % self.uuid)
        logger.setLevel(logging.DEBUG)

        for handler in logger.handlers:
            logger.removeHandler(handler)

        formatter = logging.Formatter('%(asctime)s: %(message)s')
        logfp = logging.FileHandler(logpath)
        logfp.setLevel(logging.DEBUG)
        logfp.setFormatter(formatter)

        logger.addHandler(logfp)

        return logger

    def logfilename(self):
        LOG.debug('Determining config logfile name for mirror %s.' % (self.uuid))
        path = os.path.join('mirror_%s.log' % (self.uuid))

        return path

    def logpath(self):
        path = os.path.join(self.basepath, self.logfilename())  # basepath is gauranteed to exist, so no need to check and create

        return path

    def log_url(self):
        return '%s/%s/%s' % (settings.MIRRORSVC_BASE_URL, self.uuid, self.logpath())


@python_2_unicode_compatible
class Architecture(models.Model):
    name = models.CharField(max_length=50)
    apt_mirror_prefix = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Snapshot(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    mirrorset = models.ForeignKey(MirrorSet)
    visible_to_v1_api = models.BooleanField(default=False)

    @property
    def basepath(self):
        d = os.path.join(settings.MIRRORSVC_BASE_PATH, 'snapshots', str(self.uuid))
        if not os.path.isdir(d):
            os.makedirs(d)
            if self.visible_to_v1_api:
                os.symlink(d, os.path.join(settings.MIRRORSVC_BASE_PATH, 'snapshots', str(self.id)))
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

        super(Snapshot, self).save(*args, **kwargs)

        if perform_snapshot:
            tasks.perform_snapshot.apply_async((self.id,), countdown=5)

    def perform_snapshot(self):
        self.sync_dists()
        self.symlink_pool()

    def user_can_modify(self, user):
        return user == self.mirrorset.owner


class Tags(models.Model):
    snapshot = models.ForeignKey(Snapshot, related_name='tags')
    tag = models.CharField(max_length=200)

    class meta:
        unique_together = ('snapshot', 'tag',)

    def save(self, *args, **kwargs):
        self.tag = self.tag.strip()
        super(Tags, self).save(*args, **kwargs)

    def user_can_modify(self, user):
        return self.snapshot.user_can_modify(user)
