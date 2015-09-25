from django.contrib.auth.models import User, Group
from rest_framework import serializers
from rest_framework_nested import relations

from . import models


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('self', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('self', 'name')

class RepositoryField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        if hasattr(self, 'context') and 'request' in self.context:
            return models.Repository.lookup_by_user(self.context['request'].user)

        return super(RepositoryField, self).get_queryset()


class PackageSourceSerializer(serializers.HyperlinkedModelSerializer):
    git_repository = serializers.URLField(source='git_url', required=True)
    git_branch = serializers.SlugField(source='branch', required=True)
    repository = RepositoryField(view_name='repository-detail', source='series.repository', queryset=models.Repository.objects.all())

    class Meta:
        model = models.PackageSource
        fields = ('self', 'git_repository', 'git_branch', 'repository')

    def validate_repository(self, value):
        return value.first_series()

    def validate(self, data):
        res = super(PackageSourceSerializer, self).validate(data)
        res['series'] = res['series']['repository']
        return res


class SeriesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Series
        fields = ('self', 'name', 'repository', 'binary_source_list', 'source_source_list')


class BuildRecordSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.BuildRecord
        fields = ('self', 'source', 'version', 'build_started', 'sha', 'buildlog_url')


class ExternalDependencySerializer(serializers.HyperlinkedModelSerializer):
    repository = RepositoryField(view_name='repository-detail', source='own_series.repository', queryset=models.Repository.objects.all())

    class Meta:
        model = models.ExternalDependency
        fields = ('self', 'url', 'series', 'components', 'repository', 'key')

    def validate_repository(self, value):
        return value.first_series()

    def validate(self, data):
        res = super(ExternalDependencySerializer, self).validate(data)
        if 'own_series' in res:
            res['own_series'] = res['own_series']['repository']
        return res


class RepositorySerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    binary_source_list = serializers.ReadOnlyField(source='first_series.binary_source_list')
    source_source_list = serializers.ReadOnlyField(source='first_series.source_source_list')
    sources = serializers.HyperlinkedIdentityField(view_name='packagesource-list', lookup_url_kwarg='repository_pk', lookup_field='pk', read_only=True)
    external_dependencies = serializers.HyperlinkedIdentityField(view_name='externaldependency-list', lookup_url_kwarg='repository_pk', lookup_field='pk', read_only=True)

    class Meta:
        model = models.Repository
        fields = ('self', 'user', 'name', 'key_id', 'sources', 'binary_source_list', 'source_source_list', 'external_dependencies')
