from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from django.conf import settings

from rest_auth.registration.views import SocialLoginView

from rest_framework import filters
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from aasemble.django.apps.api.v1.views import aaSembleV1Views
from aasemble.django.apps.mirrorsvc import models as mirrorsvc_models

from . import serializers as serializers_


class GithubLogin(SocialLoginView):
    callback_url = settings.GITHUB_AUTH_CALLBACK
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client


class aaSembleV2Views(aaSembleV1Views):
    view_prefix = 'v2'
    default_lookup_field = 'uuid'
    default_lookup_value_regex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    serializers = serializers_.aaSembleAPIv2Serializers()

    def BuildViewSetFactory(selff):
        BuildViewSet = super(aaSembleV2Views, selff).BuildViewSetFactory()
        BuildViewSet.filter_backends = (filters.OrderingFilter,)
        BuildViewSet.ordering = ('build_started',)
        return BuildViewSet

    def SnapshotViewSetFactory(selff):
        class SnapshotViewSet(viewsets.ModelViewSet):
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

                tag = self.request.query_params.get('tag', None)
                if tag is not None:
                    qs.filter(tags__tag=tag)

                return qs

            def perform_update(self, serializer):
                if 'mirrorset' in self.request.data or 'timestamp' in self.request.data:
                    raise ValidationError({'detail': 'Method "PATCH" not allowed.'})
                serializer.save(owner=self.request.user)

        return SnapshotViewSet
