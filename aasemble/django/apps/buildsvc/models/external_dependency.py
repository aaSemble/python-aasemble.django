import uuid

from django.db import models

from aasemble.django.apps.buildsvc.models.series import Series


class ExternalDependency(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    url = models.URLField()
    series = models.CharField(max_length=200)
    components = models.CharField(max_length=200, null=True, blank=True)
    own_series = models.ForeignKey(Series)
    key = models.TextField()

    @property
    def deb_line(self):
        return '\n'.join(self.deb_lines)

    @property
    def deb_lines(self):
        return ['deb %s %s %s' % (self.url, series, self.components) for series in self.series.split(' ')]

    def user_can_modify(self, user):
        return self.own_series.user_can_modify(user)

    @classmethod
    def lookup_by_user(cls, user):
        if not user.is_active:
            return cls.objects.none()
        if user.is_superuser:
            return cls.objects.all()
        return cls.objects.filter(own_series__repository__user=user) | cls.objects.filter(own_series__repository__extra_admins__in=user.groups.all())
