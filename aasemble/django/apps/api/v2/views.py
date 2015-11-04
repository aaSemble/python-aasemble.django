from django.conf import settings
from django.contrib.sites import models as site_models
import django.db.utils

from rest_framework import viewsets
from rest_framework.decorators import detail_route

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_auth.registration.views import SocialLoginView

from aasemble.django.apps.buildsvc import models as buildsvc_models
from aasemble.django.apps.mirrorsvc import models as mirrorsvc_models
from aasemble.django.exceptions import DuplicateResourceException

from . import serializers


class GithubLogin(SocialLoginView):
    callback_url = settings.GITHUB_AUTH_CALLBACK
    adapter_class = GitHubOAuth2Adapter
    client_class =  OAuth2Client


class MyUserAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        if not user.username:
            user.username = user.email

    def get_email_confirmation_url(self, request, emailconfirmation):
        return settings.EMAIL_CONFIRMATION_URL % (emailconfirmation.key,)


class MirrorViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirrors to be viewed or edited.
    """
    queryset = mirrorsvc_models.Mirror.objects.all()
    serializer_class = serializers.MirrorSerializer

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user) | self.queryset.filter(public=True)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @detail_route(methods=['post'])
    def refresh(self, request, pk=None):
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

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SnapshotViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirrors to be viewed or edited.
    """
    queryset = mirrorsvc_models.Snapshot.objects.all()
    serializer_class = serializers.SnapshotSerializer

    def get_queryset(self):
        return self.queryset.filter(mirrorset__owner=self.request.user)


class RepositoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows repositories to be viewed or edited.
    """
    queryset = buildsvc_models.Repository.objects.all()
    serializer_class = serializers.RepositorySerializer

    def get_queryset(self):
        return buildsvc_models.Repository.lookup_by_user(self.request.user)

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except django.db.utils.IntegrityError as e:
            raise DuplicateResourceException()


class SeriesViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows series to be viewed or edited.
    """
    queryset = buildsvc_models.Series.objects.all()
    serializer_class = serializers.SeriesSerializer

    def get_queryset(self):
        return self.queryset.filter(repository=buildsvc_models.Repository.lookup_by_user(self.request.user))


class PackageSourceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows series to be viewed or edited.
    """
    queryset = buildsvc_models.PackageSource.objects.all()
    serializer_class = serializers.PackageSourceSerializer

    def get_queryset(self):
        qs = self.queryset.filter(series__repository=buildsvc_models.Repository.lookup_by_user(self.request.user))
        if hasattr(self, 'request') and hasattr(self.request, 'resolver_match'):
            fn, args, kwargs = self.request.resolver_match
            if 'repository_pk' in kwargs:
                qs = qs.filter(series__repository=kwargs['repository_pk'])

        return qs


class ExternalDependencyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows external dependencies to be viewed or edited.
    """
    queryset = buildsvc_models.ExternalDependency.objects.all()
    serializer_class = serializers.ExternalDependencySerializer


    def get_queryset(self):
        qs = self.queryset.filter(own_series__repository=buildsvc_models.Repository.lookup_by_user(self.request.user))
        if hasattr(self, 'request') and hasattr(self.request, 'resolver_match'):
            fn, args, kwargs = self.request.resolver_match
            if 'repository_pk' in kwargs:
                qs = qs.filter(own_series__repository=kwargs['repository_pk'])

        return qs


class BuildViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows builds viewed
    """
    queryset = buildsvc_models.BuildRecord.objects.all()
    serializer_class = serializers.BuildRecordSerializer

    def get_queryset(self):
        qs = self.queryset.filter(source__series__repository=buildsvc_models.Repository.lookup_by_user(self.request.user))
        if hasattr(self, 'request') and hasattr(self.request, 'resolver_match'):
            fn, args, kwargs = self.request.resolver_match
            if 'source_pk' in kwargs:
                qs = qs.filter(source=kwargs['source_pk'])

        return qs
