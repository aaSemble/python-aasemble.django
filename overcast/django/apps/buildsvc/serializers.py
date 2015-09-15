from django.contrib.auth.models import User, Group
from rest_framework import serializers
from rest_framework_nested import relations

from . import models


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class PackageSourceSerializer(serializers.HyperlinkedModelSerializer):
    git_repository = serializers.ReadOnlyField(source='github_repository.url')
    git_branch = serializers.ReadOnlyField(source='branch')
    repository = serializers.HyperlinkedRelatedField(view_name='repository-detail', source='series.repository', read_only=True)

    class Meta:
        model = models.PackageSource
        fields = ('url', 'git_repository', 'git_branch', 'repository')


class SeriesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Series
        fields = ('url', 'name', 'repository', 'binary_source_list', 'source_source_list')


class RepositorySerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
#    series = relations.HyperlinkedRouterField(view_name='series-list', lookup_url_kwarg='repository_pk', lookup_field='pk', read_only=True)
    sources = relations.HyperlinkedRouterField(view_name='packagesource-list', lookup_url_kwarg='repository_pk', lookup_field='pk', read_only=True)

    class Meta:
        model = models.Repository
        fields = ('url', 'user', 'name', 'key_id', 'sources') # 'series', 
