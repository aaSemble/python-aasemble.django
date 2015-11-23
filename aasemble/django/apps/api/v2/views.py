from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from django.conf import settings
import django.db.utils

from rest_auth.registration.views import SocialLoginView

from rest_framework import filters, mixins, viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from aasemble.django.apps.buildsvc import models as buildsvc_models
from aasemble.django.apps.mirrorsvc import models as mirrorsvc_models
from aasemble.django.exceptions import DuplicateResourceException
from rest_framework.exceptions import ValidationError

from . import serializers


class GithubLogin(SocialLoginView):
    callback_url = settings.GITHUB_AUTH_CALLBACK
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client


class MirrorViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirrors to be viewed or edited.
    """
    queryset = mirrorsvc_models.Mirror.objects.all()
    serializer_class = serializers.MirrorSerializer
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def get_queryset(self):
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


class MirrorSetViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirrors to be viewed or edited.
    """
    queryset = mirrorsvc_models.MirrorSet.objects.all()
    serializer_class = serializers.MirrorSetSerializer
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def get_queryset(self):
        return self.queryset.filter(owner_id=self.request.user.id)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SnapshotViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirrors to be viewed or edited.
    """
    queryset = mirrorsvc_models.Snapshot.objects.all()
    serializer_class = serializers.SnapshotSerializer
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def get_queryset(self):
        return self.queryset.filter(mirrorset__owner_id=self.request.user.id)

    def perform_update(self, serializer):
        if 'mirrorset' in self.request.data or 'timestamp' in self.request.data:
            raise ValidationError({'detail': 'Method "PATCH" not allowed.'})
        serializer.save(owner=self.request.user)



class RepositoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows repositories to be viewed or edited.
    """
    queryset = buildsvc_models.Repository.objects.all()
    serializer_class = serializers.RepositorySerializer
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def get_queryset(self):
        return buildsvc_models.Repository.lookup_by_user(self.request.user)

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except django.db.utils.IntegrityError:
            raise DuplicateResourceException()


class SeriesViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows series to be viewed or edited.
    """
    queryset = buildsvc_models.Series.objects.all()
    serializer_class = serializers.SeriesSerializer
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def get_queryset(self):
        return self.queryset.filter(repository__in=buildsvc_models.Repository.lookup_by_user(self.request.user))


class PackageSourceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows series to be viewed or edited.
    """
    queryset = buildsvc_models.PackageSource.objects.all()
    serializer_class = serializers.PackageSourceSerializer
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def get_queryset(self):
        qs = self.queryset.filter(series__repository__in=buildsvc_models.Repository.lookup_by_user(self.request.user))
        if hasattr(self, 'request') and hasattr(self.request, 'resolver_match'):
            fn, args, kwargs = self.request.resolver_match
            if 'repository_uuid' in kwargs:
                qs = qs.filter(series__repository__uuid=kwargs['repository_uuid'])

        return qs


class ExternalDependencyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows external dependencies to be viewed or edited.
    """
    queryset = buildsvc_models.ExternalDependency.objects.all()
    serializer_class = serializers.ExternalDependencySerializer
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def get_queryset(self):
        qs = self.queryset.filter(own_series__repository__in=buildsvc_models.Repository.lookup_by_user(self.request.user))
        if hasattr(self, 'request') and hasattr(self.request, 'resolver_match'):
            fn, args, kwargs = self.request.resolver_match
            if 'repository_uuid' in kwargs:
                qs = qs.filter(own_series__repository__uuid=kwargs['repository_uuid'])

        return qs


class BuildViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows builds viewed
    """
    queryset = buildsvc_models.BuildRecord.objects.all()
    serializer_class = serializers.BuildRecordSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering = ('build_started',)
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

    def get_queryset(self):
        qs = self.queryset.filter(source__series__repository__in=buildsvc_models.Repository.lookup_by_user(self.request.user))
        if hasattr(self, 'request') and hasattr(self.request, 'resolver_match'):
            fn, args, kwargs = self.request.resolver_match
            if 'source_uuid' in kwargs:
                qs = qs.filter(source__uuid=kwargs['source_uuid'])

        return qs
