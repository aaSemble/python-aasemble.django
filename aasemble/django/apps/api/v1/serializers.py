from rest_framework import serializers
from django.contrib.auth import get_user_model

from aasemble.django.apps.buildsvc import models as buildsvc_models
from aasemble.django.apps.mirrorsvc import models as mirrorsvc_models


class SimpleListField(serializers.ListField):
    child = serializers.CharField()

    def to_internal_value(self, data):
        return ' '.join(data)

    def to_representation(self, data):
        if isinstance(data, list):
            return data
        return data.split(' ')


class MirrorSerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedRelatedField(view_name='v1_mirror-detail', read_only=True, source='*')
    url = serializers.URLField(required=True)
    series = SimpleListField(required=True)
    components = SimpleListField(required=True)
    public = serializers.BooleanField(default=False)
    refresh_in_progress = serializers.BooleanField(read_only=True)

    class Meta:
        model = mirrorsvc_models.Mirror
        fields = ('self', 'url', 'series', 'components', 'public', 'refresh_in_progress')


class MirrorField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        if hasattr(self, 'context') and 'request' in self.context:
            return mirrorsvc_models.Mirror.objects.filter(owner=self.context['request'].user)

        return super(MirrorField, self).get_queryset()


class MirrorSetSerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedRelatedField(view_name='v1_mirrorset-detail', read_only=True, source='*')
    mirrors = MirrorField(many=True, view_name='v1_mirror-detail', queryset=mirrorsvc_models.Mirror.objects.all())

    class Meta:
        model = mirrorsvc_models.MirrorSet
        fields = ('self', 'mirrors')


class SnapshotSerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedRelatedField(view_name='v1_snapshot-detail', read_only=True, source='*')
    mirrorset = serializers.HyperlinkedRelatedField(view_name='v1_mirrorset-detail', read_only=True)

    class Meta:
        model = mirrorsvc_models.Snapshot
        fields = ('self', 'timestamp', 'mirrorset')


class UserDetailsSerializer(serializers.ModelSerializer):
    real_name = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        return self.get_github_field(obj, 'avatar_url')

    def get_company(self, obj):
        return self.get_github_field(obj, 'company')

    def get_real_name(self, obj):
        return self.get_github_field(obj, 'name')

    def get_github_field(self, obj, field_name, default_value=None):
        gh_accounts = obj.socialaccount_set.filter(provider='github')
        if gh_accounts:
            return gh_accounts[0].extra_data[field_name]

        return default_value

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'real_name', 'company', 'avatar')
        read_only_fields = ('email', 'real_name', 'company', 'avatar')


class RepositoryField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        if hasattr(self, 'context') and 'request' in self.context:
            return buildsvc_models.Repository.lookup_by_user(self.context['request'].user)

        return super(RepositoryField, self).get_queryset()


class PackageSourceSerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedRelatedField(view_name='v1_packagesource-detail', read_only=True, source='*')
    git_repository = serializers.URLField(source='git_url', required=True)
    git_branch = serializers.SlugField(source='branch', required=True)
    repository = RepositoryField(view_name='v1_repository-detail', source='series.repository', queryset=buildsvc_models.Repository.objects.all())
    builds = serializers.HyperlinkedIdentityField(view_name='v1_build-list', lookup_url_kwarg='source_pk', lookup_field='pk', read_only=True)

    class Meta:
        model = buildsvc_models.PackageSource
        fields = ('self', 'git_repository', 'git_branch', 'repository', 'builds')

    def validate_repository(self, value):
        return value.first_series()

    def validate(self, data):
        res = super(PackageSourceSerializer, self).validate(data)
        res['series'] = res['series']['repository']
        return res


class SeriesSerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedRelatedField(view_name='v1_series-detail', read_only=True, source='*')

    class Meta:
        model = buildsvc_models.Series
        fields = ('self', 'name', 'repository', 'binary_source_list', 'source_source_list')


class BuildRecordSerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedRelatedField(view_name='v1_buildrecord-detail', read_only=True, source='*')
    source = serializers.HyperlinkedRelatedField(view_name='v1_packagesource-detail', read_only=True)

    class Meta:
        model = buildsvc_models.BuildRecord
        fields = ('self', 'source', 'version', 'build_started', 'sha', 'buildlog_url')


class ExternalDependencySerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedRelatedField(view_name='v1_externaldependency-detail', read_only=True, source='*')
    repository = RepositoryField(view_name='v1_repository-detail', source='own_series.repository', queryset=buildsvc_models.Repository.objects.all())

    class Meta:
        model = buildsvc_models.ExternalDependency
        fields = ('self', 'url', 'series', 'components', 'repository', 'key')

    def validate_repository(self, value):
        return value.first_series()

    def validate(self, data):
        res = super(ExternalDependencySerializer, self).validate(data)
        if 'own_series' in res:
            res['own_series'] = res['own_series']['repository']
        return res


class RepositorySerializer(serializers.HyperlinkedModelSerializer):
    self = serializers.HyperlinkedRelatedField(view_name='v1_repository-detail', read_only=True, source='*')
    user = serializers.ReadOnlyField(source='user.username')
    key_id = serializers.CharField(read_only=True)
    binary_source_list = serializers.ReadOnlyField(source='first_series.binary_source_list')
    source_source_list = serializers.ReadOnlyField(source='first_series.source_source_list')
    sources = serializers.HyperlinkedIdentityField(view_name='v1_packagesource-list', lookup_url_kwarg='repository_pk', lookup_field='pk', read_only=True)
    external_dependencies = serializers.HyperlinkedIdentityField(view_name='v1_externaldependency-list', lookup_url_kwarg='repository_pk', lookup_field='pk', read_only=True)

    class Meta:
        model = buildsvc_models.Repository
        fields = ('self', 'user', 'name', 'key_id', 'sources', 'binary_source_list', 'source_source_list', 'external_dependencies')
