from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .forms import MirrorDefinitionForm, MirrorSetDefinitionForm
from .models import Mirror, MirrorSet, Snapshot


def get_mirror_definition_form(request, *args, **kwargs):
    form = MirrorDefinitionForm(*args, **kwargs)
    return form


@login_required
def mirror_definition(request, mirror_uuid):
    # print("entered mirror_definition function")
    if mirror_uuid == 'new':
        # print("mirror_uuid==new")
        mirror = None
    else:
        mirror = Mirror.objects.get(uuid=mirror_uuid)
        if not mirror.user_can_modify(request.user):
            mirror, mirror_uuid = None, 'new'

    if request.method == 'POST':
        # print("Entered request.method == POST")
        form = get_mirror_definition_form(request, request.POST, instance=mirror)

        if mirror is not None and request.POST.get('delete', '') == 'delete':
            mirror.delete()
            return HttpResponseRedirect(reverse('mirrorsvc:mirrors'))

        if form.is_valid():
            new_mirror = form.save(commit=False)
            new_mirror.owner = request.user
            new_mirror.save()
            return HttpResponseRedirect(reverse('mirrorsvc:mirrors'))
    else:
        form = get_mirror_definition_form(request, instance=mirror)

    return render(request, 'mirrorsvc/html/mirror_definition.html',
                  {'form': form, 'mirror_uuid': mirror_uuid})


def get_mirrorset_definition_form(request, *args, **kwargs):
    form = MirrorSetDefinitionForm(*args, **kwargs)
    return form


@login_required
def mirrorset_definition(request, uuid):
    # print("entered mirrorset_definition function")
    if uuid == 'new':
        # print("mirrorset_uuid==new")
        mirrorset = None
    else:
        mirrorset = MirrorSet.objects.get(uuid=uuid)
        if not mirrorset.user_can_modify(request.user):
            mirrorset, uuid = None, 'new'

    if request.method == 'POST':
        # print("Entered request.method == POST")
        form = get_mirrorset_definition_form(request, request.POST, instance=mirrorset)

        if mirrorset is not None and request.POST.get('delete', '') == 'delete':
            mirrorset.delete()
            return HttpResponseRedirect(reverse('mirrorsvc:mirrorsets'))

        if form.is_valid():
            new_mirrorset = form.save(commit=False)
            new_mirrorset.owner = request.user
            new_mirrorset.save()
            print("new_mirrorset saved")
            return HttpResponseRedirect(reverse('mirrorsvc:mirrorsets'))
    else:
        form = get_mirrorset_definition_form(request, instance=mirrorset)

    return render(request, 'mirrorsvc/html/mirrorset_definition.html',
                  {'form': form, 'uuid': uuid})


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


@login_required
def refresh_mirror_with_uuid(request, mirror_uuid):
    mirror = Mirror.objects.get(uuid=mirror_uuid)
    if mirror.user_can_modify(request.user):
        mirror.schedule_update_mirror()
    return HttpResponseRedirect(reverse('mirrorsvc:mirrors'))
