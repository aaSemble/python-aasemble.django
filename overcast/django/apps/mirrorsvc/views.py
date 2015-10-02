from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response

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
