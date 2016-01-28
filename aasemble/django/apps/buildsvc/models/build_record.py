import logging
import os
import os.path
import socket
import uuid

from django.conf import settings
from django.db import models

from aasemble.django.apps.buildsvc.models.package_source import PackageSource
from aasemble.django.utils import ensure_dir

LOG = logging.getLogger(__name__)


class BuildRecord(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(PackageSource)
    version = models.CharField(max_length=50)
    build_counter = models.IntegerField(default=0)
    build_started = models.DateTimeField(auto_now_add=True)
    build_finished = models.DateTimeField(blank=True, null=True)
    sha = models.CharField(max_length=100, null=True, blank=True)
    handler_node = models.CharField(max_length=100, default=socket.getfqdn, null=True)

    def __init__(self, *args, **kwargs):
        self._logger = None
        self._saved_logpath = None
        return super(BuildRecord, self).__init__(*args, **kwargs)

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('v3_buildrecord-detail', args=[str(self.uuid)])

    def buildlog_url(self):
        from django.core.urlresolvers import reverse
        return reverse('v3_buildrecord-log', args=[str(self.uuid)])

    @property
    def logger(self):
        logpath = self.temporary_log_path()

        if self._logger is None:
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

        return self._logger

    def temporary_log_path(self):
        return os.path.join(ensure_dir(settings.AASEMBLE_BUILDSVC_BUILDLOG_TMPDIR), str(self.uuid))

    def logpath(self):
        LOG.debug('Determining logpath for %s. version = %r' % (self, self.version))
        if self.version:
            return os.path.join(self.source.long_name, '%s_%s.log' % (self.source.long_name, self.version))
        else:
            return os.path.join(self.source.long_name, '%s_%s.tmp.log' % (self.source.long_name, self.build_counter))

    def save(self, *args, **kwargs):
        if self.build_finished and self.pk:
            old = BuildRecord.objects.get(pk=self.pk)
            if not old.build_finished:
                with open(self.final_log_path(), 'wb') as outfp:
                    with open(self.temporary_log_path(), 'rb') as infp:
                        while True:
                            buf = infp.read(4096)
                            if not buf:
                                break
                            outfp.write(buf)
        return super(BuildRecord, self).save(*args, **kwargs)

    def final_log_path(self):
        path = os.path.join(self.source.series.repository.buildlogdir,
                            self.logpath())

        dirpath = os.path.dirname(path)

        if not os.path.isdir(dirpath):
            os.makedirs(dirpath)

        return path

    def direct_buildlog_url(self):
        return '%s/buildlogs/%s' % (self.source.series.repository.base_url, self.logpath())

    @property
    def duration(self):
        if self.build_started and self.build_finished:
            return (self.build_finished - self.build_started).total_seconds()
