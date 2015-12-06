from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from django.conf import settings
from django.conf.urls import include, url
import django.db.utils

from rest_auth.registration.views import SocialLoginView

from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from rest_framework_nested import routers

from aasemble.django.apps.buildsvc import models as buildsvc_models
from aasemble.django.apps.mirrorsvc import models as mirrorsvc_models
from aasemble.django.exceptions import DuplicateResourceException

from . import serializers as serializers_


class GithubLogin(SocialLoginView):
    callback_url = settings.GITHUB_AUTH_CALLBACK
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client


class aaSembleV1ViewSet(viewsets.ModelViewSet):
    def __new__(cls, *args, **kwargs):
        bases = (cls,) + cls.__bases__
        try:
            from rest_framework_tracking.mixins import LoggingMixin
            if 'rest_framework_tracking' in settings.INSTALLED_APPS:
                bases = (LoggingMixin,) + bases
        except ImportError:
            pass
        return viewsets.ModelViewSet.__new__(type('aaSembleV1ViewSet', bases, dict(cls.__dict__)))


class aaSembleV1ReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    def __new__(cls, *args, **kwargs):
        bases = (cls,) + cls.__bases__
        try:
            from rest_framework_tracking.mixins import LoggingMixin
            if 'rest_framework_tracking' in settings.INSTALLED_APPS:
                bases = (LoggingMixin,) + bases
        except ImportError:
            pass
        return viewsets.ReadOnlyModelViewSet.__new__(type('aaSembleV1ReadOnlyViewSet', bases, dict(cls.__dict__)))


class aaSembleV1Views(object):
    view_prefix = 'v1'
    default_lookup_field = 'pk'
    default_lookup_value_regex = '[^/]+'
    serializers = serializers_.aaSembleAPIv1Serializers()

    def __init__(self):
        self.MirrorViewSet = self.MirrorViewSetFactory()
        self.MirrorSetViewSet = self.MirrorSetViewSetFactory()
        self.SnapshotViewSet = self.SnapshotViewSetFactory()
        self.RepositoryViewSet = self.RepositoryViewSetFactory()
        self.SeriesViewSet = self.SeriesViewSetFactory()
        self.PackageSourceViewSet = self.PackageSourceViewSetFactory()
        self.ExternalDependencyViewSet = self.ExternalDependencyViewSetFactory()
        self.BuildViewSet = self.BuildViewSetFactory()
        self.urls = self.build_urls()

    def MirrorViewSetFactory(selff):
        class MirrorViewSet(aaSembleV1ViewSet):
            """
            API endpoint that allows mirrors to be viewed or edited.
            """
            lookup_field = selff.default_lookup_field
            lookup_value_regex = selff.default_lookup_value_regex
            queryset = mirrorsvc_models.Mirror.objects.all()
            serializer_class = selff.serializers.MirrorSerializer

            def get_queryset(self):
                if self.request.user.is_superuser:
                    return self.queryset.all()
                return self.queryset.filter(owner_id=self.request.user.id) | self.queryset.filter(public=True)

            def perform_create(self, serializer):
                serializer.save(owner=self.request.user)

            @detail_route(methods=['post'])
            def refresh(self, request, **kwargs):
                mirror = self.get_object()
                scheduled = mirror.schedule_update_mirror()
                if scheduled:
                    status = 'update scheduled'
                else:
                    status = 'update already scheduled'
                return Response({'status': status})

        return MirrorViewSet

    def MirrorSetViewSetFactory(selff):
        class MirrorSetViewSet(aaSembleV1ViewSet):
            """
            API endpoint that allows mirrors to be viewed or edited.
            """
            lookup_field = selff.default_lookup_field
            lookup_value_regex = selff.default_lookup_value_regex
            queryset = mirrorsvc_models.MirrorSet.objects.all()
            serializer_class = selff.serializers.MirrorSetSerializer

            def get_queryset(self):
                if self.request.user.is_superuser:
                    return self.queryset.all()
                return self.queryset.filter(owner_id=self.request.user.id)

            def perform_create(self, serializer):
                serializer.save(owner=self.request.user)

        return MirrorSetViewSet

    def SnapshotViewSetFactory(selff):
        class SnapshotViewSet(aaSembleV1ViewSet):
            lookup_field = selff.default_lookup_field
            lookup_value_regex = selff.default_lookup_value_regex
            """
            API endpoint that allows mirrors to be viewed or edited.
            """
            queryset = mirrorsvc_models.Snapshot.objects.all()
            serializer_class = selff.serializers.SnapshotSerializer

            def get_queryset(self):
                if self.request.user.is_superuser:
                    qs = self.queryset.all()
                else:
                    qs = self.queryset.filter(mirrorset__owner_id=self.request.user.id)

                if selff.view_prefix == 'v1':
                    qs = qs.exclude(visible_to_v1_api=False)

                tag = self.request.query_params.get('tag', None)
                if tag is not None:
                    qs.filter(tags__tag=tag)

                return qs

            def perform_update(self, serializer):
                if 'mirrorset' in self.request.data or 'timestamp' in self.request.data:
                    raise ValidationError({'detail': 'Method "PATCH" not allowed.'})
                serializer.save(owner=self.request.user)

        return SnapshotViewSet

    def RepositoryViewSetFactory(selff):
        class RepositoryViewSet(aaSembleV1ViewSet):
            """
            API endpoint that allows repositories to be viewed or edited.
            """
            lookup_field = selff.default_lookup_field
            lookup_value_regex = selff.default_lookup_value_regex
            queryset = buildsvc_models.Repository.objects.all()
            serializer_class = selff.serializers.RepositorySerializer

            def get_queryset(self):
                return buildsvc_models.Repository.lookup_by_user(self.request.user)

            def perform_create(self, serializer):
                try:
                    serializer.save(user=self.request.user)
                except django.db.utils.IntegrityError:
                    raise DuplicateResourceException()

        return RepositoryViewSet

    def SeriesViewSetFactory(selff):
        class SeriesViewSet(aaSembleV1ViewSet):
            """
            API endpoint that allows series to be viewed or edited.
            """
            lookup_field = selff.default_lookup_field
            lookup_value_regex = selff.default_lookup_value_regex
            queryset = buildsvc_models.Series.objects.all()
            serializer_class = selff.serializers.SeriesSerializer

            def get_queryset(self):
                return self.queryset.filter(repository__in=buildsvc_models.Repository.lookup_by_user(self.request.user))

        return SeriesViewSet

    def get_qs_filter(selff, kwargs, base_key, base_value):
        key = '{0}__{1}'.format(base_key, selff.default_lookup_field)
        value = '{0}_{1}'.format(base_value, selff.default_lookup_field)
        return {key: kwargs[value]}

    def PackageSourceViewSetFactory(selff):
        class PackageSourceViewSet(aaSembleV1ViewSet):
            """
            API endpoint that allows series to be viewed or edited.
            """
            lookup_field = selff.default_lookup_field
            lookup_value_regex = selff.default_lookup_value_regex
            queryset = buildsvc_models.PackageSource.objects.select_related('series__repository__user')
            serializer_class = selff.serializers.PackageSourceSerializer

            def get_queryset(self):
                qs = self.queryset.filter(series__repository__in=buildsvc_models.Repository.lookup_by_user(self.request.user))
                if 'repository_{0}'.format(selff.default_lookup_field) in self.kwargs:
                    qs = qs.filter(**selff.get_qs_filter(self.kwargs, 'series__repository', 'repository'))

                return qs

        return PackageSourceViewSet

    def ExternalDependencyViewSetFactory(selff):
        class ExternalDependencyViewSet(aaSembleV1ViewSet):
            """
            API endpoint that allows external dependencies to be viewed or edited.
            """
            lookup_field = selff.default_lookup_field
            lookup_value_regex = selff.default_lookup_value_regex
            queryset = buildsvc_models.ExternalDependency.objects.all()
            serializer_class = selff.serializers.ExternalDependencySerializer

            def get_queryset(self):
                qs = self.queryset.filter(own_series__repository__in=buildsvc_models.Repository.lookup_by_user(self.request.user))

                if 'repository_{0}'.format(selff.default_lookup_field) in self.kwargs:
                    qs = qs.filter(**selff.get_qs_filter(self.kwargs, 'own_series__repository', 'repository'))

                return qs

        return ExternalDependencyViewSet

    def BuildViewSetFactory(selff):
        class BuildViewSet(aaSembleV1ReadOnlyViewSet):
            """
            API endpoint that allows builds viewed
            """
            lookup_field = selff.default_lookup_field
            lookup_value_regex = selff.default_lookup_value_regex
            queryset = buildsvc_models.BuildRecord.objects.all().select_related('source__series__repository__user')
            serializer_class = selff.serializers.BuildRecordSerializer

            def get_queryset(self):
                qs = self.queryset.filter(source__series__repository__in=buildsvc_models.Repository.lookup_by_user(self.request.user))
                if 'source_{0}'.format(selff.default_lookup_field) in self.kwargs:
                    qs = qs.filter(**selff.get_qs_filter(self.kwargs, 'source', 'source'))

                return qs

        return BuildViewSet

    def build_urls(self):
        router = routers.DefaultRouter()
        router.register(r'repositories', self.RepositoryViewSet, base_name='{0}_repository'.format(self.view_prefix))
        router.register(r'external_dependencies', self.ExternalDependencyViewSet, base_name='{0}_externaldependency'.format(self.view_prefix))
        router.register(r'sources', self.PackageSourceViewSet, base_name='{0}_packagesource'.format(self.view_prefix))
        router.register(r'builds', self.BuildViewSet, base_name='{0}_buildrecord'.format(self.view_prefix))
        router.register(r'mirrors', self.MirrorViewSet, base_name='{0}_mirror'.format(self.view_prefix))
        router.register(r'mirror_sets', self.MirrorSetViewSet, base_name='{0}_mirrorset'.format(self.view_prefix))
        router.register(r'snapshots', self.SnapshotViewSet, base_name='{0}_snapshot'.format(self.view_prefix))

        source_router = routers.NestedSimpleRouter(router, r'sources', lookup='source')
        source_router.register(r'builds', self.BuildViewSet, base_name='{0}_build'.format(self.view_prefix))

        repository_router = routers.NestedSimpleRouter(router, r'repositories', lookup='repository')
        repository_router.register(r'sources', self.PackageSourceViewSet, base_name='{0}_packagesource'.format(self.view_prefix))
        repository_router.register(r'external_dependencies', self.ExternalDependencyViewSet, base_name='{0}_externaldependency'.format(self.view_prefix))

        urls = [url(r'^', include(router.urls)),
                url(r'^', include(repository_router.urls)),
                url(r'^', include(source_router.urls)),
                url(r'^auth/', include('rest_auth.urls')),
                url(r'^auth/github/$', GithubLogin.as_view(), name='github_login')]

        if getattr(settings, 'SIGNUP_OPEN', False):
            urls += [url(r'^auth/registration/', include('rest_auth.registration.urls'))]
        return urls
