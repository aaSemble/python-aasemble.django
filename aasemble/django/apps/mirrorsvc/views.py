from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Mirror, MirrorSet, Snapshot

@login_required
def mirrors(request):
    mirrors = Mirror.lookup_by_user(request.user)
    return render(request, 'mirrorsvc/html/mirrors.html',
                  {'mirrors': mirrors})

@login_required
def snapshots(request):
    snapshots = Snapshot.objects.filter(mirrorset__in=MirrorSet.lookup_by_user(request.user)).order_by('timestamp')
    return render(request, 'mirrorsvc/html/snapshots.html',
                  {'snapshots': snapshots})

@login_required
def mirrorsets(request):
    sets = MirrorSet.lookup_by_user(request.user)
    return render(request, 'mirrorsvc/html/mirrorsets.html',
                  {'mirrorsets': sets})

@login_required
def mirrorset_snapshots(request, uuid):
    # print "Entered mirrorset_snapshots function"
    snapshots = list()
    try:
        mirrorset = MirrorSet.objects.get(uuid=uuid)
        snapshots = Snapshot.objects.filter(mirrorset=mirrorset)
    except:
        pass
    return render(request, 'mirrorsvc/html/mirrorset_snapshots.html',
                  {'snapshots': snapshots})
