from django.contrib.auth.models import User, Group
from rest_framework import serializers

from . import models


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class RepositorySerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    class Meta:
        model = models.Repository
        fields = ('url', 'user', 'name', 'key_id') #, 'series_set')


class PackageSourceSerializer(serializers.HyperlinkedModelSerializer):
    git_repository = serializers.ReadOnlyField(source='github_repository.url')
    git_branch = serializers.ReadOnlyField(source='branch')

    class Meta:
        model = models.PackageSource
        fields = ('url', 'git_repository', 'git_branch', 'series')


class SeriesSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Series
        fields = ('url', 'name', 'repository', 'binary_source_list', 'source_source_list')
