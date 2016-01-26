import logging
import os
import os.path
import uuid

from django.db import models

from aasemble.django.apps.buildsvc.models.package_source import PackageSource

LOG = logging.getLogger(__name__)


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
