from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.forms import ModelChoiceField
from django.http import HttpResponseRedirect
from django.shortcuts import render

from rest_framework import viewsets
from .serializers import MirrorSerializer, MirrorSetSerializer, SnapshotSerializer

from .models import Mirror, MirrorSet, Snapshot


#############
# API stuff #
#############

class MirrorViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirrors to be viewed or edited.
    """
    queryset = Mirror.objects.all()
    serializer_class = MirrorSerializer

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user) | self.queryset.filter(public=True)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class MirrorSetViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirrors to be viewed or edited.
    """
    queryset = MirrorSet.objects.all()
    serializer_class = MirrorSetSerializer

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SnapshotViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows mirrors to be viewed or edited.
    """
    queryset = Snapshot.objects.all()
    serializer_class = SnapshotSerializer

    def get_queryset(self):
        return self.queryset.filter(mirrorset__owner=self.request.user)
