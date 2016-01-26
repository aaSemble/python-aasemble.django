import uuid

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from aasemble.django.apps.buildsvc.models.repository import Repository


@python_2_unicode_compatible
class Series(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    repository = models.ForeignKey(Repository, related_name='series')

    def __str__(self):
        return '%s/%s' % (self.repository.name, self.name)

    def binary_source_list(self, force_trusted=False):
        return self._source_list(prefix='deb', force_trusted=force_trusted)

    def source_source_list(self, force_trusted=False):
        return self._source_list(prefix='deb-src', force_trusted=force_trusted)

    def _source_list(self, prefix, force_trusted=False):
        if force_trusted:
            option = ' [trusted=yes]'
        else:
            option = ''
        return '%s%s %s %s main' % (prefix,
                                    option,
                                    self.repository.base_url,
                                    self.name)

    class Meta:
        verbose_name_plural = 'series'

    def process_changes(self, changes_file):
        self.repository.process_changes(self.name, changes_file)

    def build_sources_list(self):
        sources = []
        for series in ('trusty', 'trusty-updates', 'trusty-security'):
            sources += ['deb http://archive.ubuntu.com/ubuntu {} main universe restricted multiverse'.format(series)]
        sources += [self.binary_source_list(force_trusted=True)]
        sources += sum([extdep.deb_lines for extdep in self.externaldependency_set.all()], [])
        return '\n'.join(sources)

    def build_apt_keys(self):
        keys = [self.repository.key_data]
        keys += [extdep.key for extdep in self.externaldependency_set.all()]
        return '\n'.join(keys)

    def export(self):
        self.repository.export()

    def user_can_modify(self, user):
        return self.repository.user_can_modify(user)
