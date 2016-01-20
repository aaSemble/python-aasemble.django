from rest_framework import serializers

from aasemble.django.apps.buildsvc import models as buildsvc_models
from aasemble.django.apps.mirrorsvc import models as mirrorsvc_models


class aaSembleAPIv1Serializers(object):
    view_prefix = 'v1'
    default_lookup_field = 'pk'
    snapshots_have_tags = False
    builds_nest_source = False
    include_build_duration = False
    include_key_data_link = False
    include_builds_link = False
    include_sources_list_in_mirrorset = False
    include_sources_list_in_mirrors = False
    sources_nest_repository = False
    repo_has_build_sources_list = False
    repo_has_series_name = False
    source_includes_last_built_version = False
    build_includes_counter = False

    def __init__(self):
        self.MirrorSerializer = self.MirrorSerializerFactory()
        self.MirrorSetSerializer = self.MirrorSetSerializerFactory()
        self.SnapshotSerializer = self.SnapshotSerializerFactory()
        self.RepositorySerializer = self.RepositorySerializerFactory()
        self.PackageSourceSerializer = self.PackageSourceSerializerFactory()
        self.SeriesSerializer = self.SeriesSerializerFactory()
        self.BuildRecordSerializer = self.BuildRecordSerializerFactory()
        self.ExternalDependencySerializer = self.ExternalDependencySerializerFactory()

    class SimpleListField(serializers.ListField):
        child = serializers.CharField()

        def to_internal_value(self, data):
            return ' '.join(data)

        def to_representation(self, data):
            if isinstance(data, list):
                return data
            return data.split(' ')

    class TagsSerializer(serializers.ListField):
        child = serializers.CharField()

        def to_internal_value(self, data):
            tags = data
            tag_val = []
            for tag in tags:
                tag_val.append(dict(tag=tag))
            return tag_val

        def to_representation(self, data):
            tags = data.all()
            tag_val = []
            for tag in tags:
                tag_val.append(tag.tag)
            return tag_val

    class MirrorField(serializers.HyperlinkedRelatedField):
        def get_queryset(self):
            if hasattr(self, 'context') and 'request' in self.context:
                return mirrorsvc_models.Mirror.objects.filter(owner=self.context['request'].user)

            return super(aaSembleAPIv1Serializers.MirrorField, self).get_queryset()

    class MirrorSetField(serializers.HyperlinkedRelatedField):
        def get_queryset(self):
            if hasattr(self, 'context') and 'request' in self.context:
                return mirrorsvc_models.MirrorSet.lookup_by_user(self.context['request'].user)

            return super(aaSembleAPIv1Serializers.MirrorSetField, self).get_queryset()

    class RepositoryField(serializers.HyperlinkedRelatedField):
        def get_queryset(self):
            if hasattr(self, 'context') and 'request' in self.context:
                return buildsvc_models.Repository.lookup_by_user(self.context['request'].user)

            return super(aaSembleAPIv1Serializers.RepositoryField, self).get_queryset()

    def MirrorSerializerFactory(selff):
        class MirrorSerializer(serializers.HyperlinkedModelSerializer):
            self = serializers.HyperlinkedRelatedField(view_name='{0}_mirror-detail'.format(selff.view_prefix), read_only=True, source='*', lookup_field=selff.default_lookup_field)
            url = serializers.URLField(required=True)
            series = selff.SimpleListField(required=True)
            components = selff.SimpleListField(required=True)
            public = serializers.BooleanField(default=False)
            refresh_in_progress = serializers.BooleanField(read_only=True)
            if selff.include_sources_list_in_mirrors:
                sources_list = serializers.CharField(read_only=True)

            def create(self, validated_data):
                return mirrorsvc_models.Mirror.objects.create(visible_to_v1_api=(selff.view_prefix == 'v1'),
                                                              **validated_data)

            class Meta:
                model = mirrorsvc_models.Mirror
                fields = ('self', 'url', 'series', 'components', 'public', 'refresh_in_progress')
                if selff.include_sources_list_in_mirrors:
                    fields += ('sources_list',)

        return MirrorSerializer

    def MirrorSetSerializerFactory(selff):
        class MirrorSetSerializer(serializers.HyperlinkedModelSerializer):
            self = serializers.HyperlinkedRelatedField(view_name='{0}_mirrorset-detail'.format(selff.view_prefix), read_only=True, source='*', lookup_field=selff.default_lookup_field)
            mirrors = selff.MirrorField(many=True, view_name='{0}_mirror-detail'.format(selff.view_prefix), queryset=mirrorsvc_models.Mirror.objects.all(), lookup_field=selff.default_lookup_field)
            if selff.include_sources_list_in_mirrorset:
                sources_list = serializers.CharField(read_only=True)

            class Meta:
                model = mirrorsvc_models.MirrorSet
                fields = ('self', 'mirrors')
                if selff.include_sources_list_in_mirrorset:
                    fields += ('sources_list',)

        return MirrorSetSerializer

    def SnapshotSerializerFactory(selff):
        class SnapshotSerializer(serializers.HyperlinkedModelSerializer):
            self = serializers.HyperlinkedRelatedField(view_name='{0}_snapshot-detail'.format(selff.view_prefix), read_only=True, source='*', lookup_field=selff.default_lookup_field)
            mirrorset = selff.MirrorSetField(view_name='{0}_mirrorset-detail'.format(selff.view_prefix), queryset=mirrorsvc_models.MirrorSet.objects.none(), lookup_field=selff.default_lookup_field)

            if selff.snapshots_have_tags:
                tags = selff.TagsSerializer(required=False)

            def create(self, validated_data):
                tags_data = validated_data.pop('tags', [])
                snapshot = mirrorsvc_models.Snapshot.objects.create(visible_to_v1_api=(selff.view_prefix == 'v1'), **validated_data)
                for tag_data in tags_data:
                    mirrorsvc_models.Tags.objects.create(snapshot=snapshot, **tag_data)
                return snapshot

            def update(self, instance, validated_data):
                tags_data = validated_data.pop('tags', [])
                mirrorsvc_models.Tags.objects.filter(snapshot=instance).delete()
                for tag_data in tags_data:
                    mirrorsvc_models.Tags.objects.create(snapshot=instance, **tag_data)
                return instance

            class Meta:
                model = mirrorsvc_models.Snapshot
                fields = ('self', 'timestamp', 'mirrorset')
                if selff.snapshots_have_tags:
                    fields += ('tags',)

        return SnapshotSerializer

    def PackageSourceSerializerFactory(selff):
        class PackageSourceSerializer(serializers.HyperlinkedModelSerializer):
            self = serializers.HyperlinkedRelatedField(view_name='{0}_packagesource-detail'.format(selff.view_prefix), read_only=True, source='*', lookup_field=selff.default_lookup_field)
            git_repository = serializers.URLField(source='git_url', required=True)
            git_branch = serializers.SlugField(source='branch', required=True)
            repository = selff.RepositoryField(view_name='{0}_repository-detail'.format(selff.view_prefix), source='series.repository', queryset=buildsvc_models.Repository.objects.all(), lookup_field=selff.default_lookup_field)
            builds = serializers.HyperlinkedIdentityField(view_name='{0}_build-list'.format(selff.view_prefix), lookup_url_kwarg='source_{0}'.format(selff.default_lookup_field), read_only=True, lookup_field=selff.default_lookup_field)

            if selff.sources_nest_repository:
                repository_info = selff.RepositorySerializer(source='repository', read_only=True)

            if selff.source_includes_last_built_version:
                last_built_version = serializers.CharField(read_only=True)

            class Meta:
                model = buildsvc_models.PackageSource
                fields = ('self', 'git_repository', 'git_branch', 'repository', 'builds')
                if selff.sources_nest_repository:
                    fields += ('repository_info',)
                if selff.source_includes_last_built_version:
                    fields += ('last_built_version',)

            def validate_repository(self, value):
                return value.first_series()

            def validate(self, data):
                res = super(PackageSourceSerializer, self).validate(data)
                res['series'] = res['series']['repository']
                return res

        return PackageSourceSerializer

    def SeriesSerializerFactory(selff):
        class SeriesSerializer(serializers.HyperlinkedModelSerializer):
            self = serializers.HyperlinkedRelatedField(view_name='{0}_series-detail'.format(selff.view_prefix), read_only=True, source='*', lookup_field=selff.default_lookup_field)

            class Meta:
                model = buildsvc_models.Series
                fields = ('self', 'name', 'repository', 'binary_source_list', 'source_source_list')

        return SeriesSerializer

    def BuildRecordSerializerFactory(selff):
        class BuildRecordSerializer(serializers.HyperlinkedModelSerializer):
            self = serializers.HyperlinkedRelatedField(view_name='{0}_buildrecord-detail'.format(selff.view_prefix), read_only=True, source='*', lookup_field=selff.default_lookup_field)

            if selff.builds_nest_source:
                source = selff.PackageSourceSerializer()
            else:
                source = serializers.HyperlinkedRelatedField(view_name='{0}_packagesource-detail'.format(selff.view_prefix), read_only=True, lookup_field=selff.default_lookup_field)

            if selff.build_includes_counter:
                build_counter = serializers.IntegerField(read_only=True)

            class Meta:
                model = buildsvc_models.BuildRecord
                fields = ('self', 'source', 'version', 'build_started', 'sha', 'buildlog_url')
                if selff.include_build_duration:
                    fields += ('duration', 'build_finished')
                if selff.build_includes_counter:
                    fields += ('build_counter',)

        return BuildRecordSerializer

    def ExternalDependencySerializerFactory(selff):
        class ExternalDependencySerializer(serializers.HyperlinkedModelSerializer):
            self = serializers.HyperlinkedRelatedField(view_name='{0}_externaldependency-detail'.format(selff.view_prefix), read_only=True, source='*', lookup_field=selff.default_lookup_field)
            repository = selff.RepositoryField(view_name='{0}_repository-detail'.format(selff.view_prefix), source='own_series.repository', queryset=buildsvc_models.Repository.objects.all(), lookup_field=selff.default_lookup_field)

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

        return ExternalDependencySerializer

    def RepositorySerializerFactory(selff):
        class RepositorySerializer(serializers.HyperlinkedModelSerializer):
            self = serializers.HyperlinkedRelatedField(view_name='{0}_repository-detail'.format(selff.view_prefix), read_only=True, source='*', lookup_field=selff.default_lookup_field)
            user = serializers.ReadOnlyField(source='user.username')
            key_id = serializers.CharField(read_only=True)
            binary_source_list = serializers.ReadOnlyField(source='first_series.binary_source_list')
            source_source_list = serializers.ReadOnlyField(source='first_series.source_source_list')
            sources = serializers.HyperlinkedIdentityField(view_name='{0}_packagesource-list'.format(selff.view_prefix), lookup_url_kwarg='repository_{0}'.format(selff.default_lookup_field), read_only=True, lookup_field=selff.default_lookup_field)
            external_dependencies = serializers.HyperlinkedIdentityField(view_name='{0}_externaldependency-list'.format(selff.view_prefix), lookup_url_kwarg='repository_{0}'.format(selff.default_lookup_field), read_only=True, lookup_field=selff.default_lookup_field)
            if selff.include_key_data_link:
                key = serializers.CharField(read_only=True, source='key_url')

            if selff.include_builds_link:
                builds = serializers.HyperlinkedIdentityField(view_name='{0}_build-list'.format(selff.view_prefix), lookup_url_kwarg='repository_{0}'.format(selff.default_lookup_field), read_only=True, lookup_field=selff.default_lookup_field)

            if selff.repo_has_build_sources_list:
                build_sources_list = serializers.HyperlinkedIdentityField(view_name='{0}_repository-build-sources-list'.format(selff.view_prefix), lookup_url_kwarg=selff.default_lookup_field, read_only=True, lookup_field=selff.default_lookup_field)
                build_apt_keys = serializers.HyperlinkedIdentityField(view_name='{0}_repository-build-apt-keys'.format(selff.view_prefix), lookup_url_kwarg=selff.default_lookup_field, read_only=True, lookup_field=selff.default_lookup_field)

            if selff.repo_has_series_name:
                series_name = serializers.CharField(read_only=True, source='first_series.name')

            class Meta:
                model = buildsvc_models.Repository
                fields = ('self', 'user', 'name', 'key_id', 'sources', 'binary_source_list', 'source_source_list', 'external_dependencies')
                if selff.include_key_data_link:
                    fields += ('key',)

                if selff.include_builds_link:
                    fields += ('builds',)

                if selff.repo_has_build_sources_list:
                    fields += ('build_sources_list', 'build_apt_keys')

                if selff.repo_has_series_name:
                    fields += ('series_name',)

        return RepositorySerializer
