from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from .forms import MirrorDefinitionForm, MirrorSetDefinitionForm, TagDefinitionForm
from .models import Mirror, MirrorSet, Snapshot, Tags


def get_mirror_definition_form(request, *args, **kwargs):
    form = MirrorDefinitionForm(*args, **kwargs)
    return form


@login_required
def mirror_definition(request, mirror_uuid):
    if mirror_uuid == 'new':
        mirror = None
    else:
        mirror = Mirror.objects.get(uuid=mirror_uuid)
        if not mirror.user_can_modify(request.user):
            mirror, mirror_uuid = None, 'new'

    if request.method == 'POST':
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
    if uuid == 'new':
        mirrorset = None
    else:
        mirrorset = MirrorSet.objects.get(uuid=uuid)
        if not mirrorset.user_can_modify(request.user):
            mirrorset, uuid = None, 'new'

    if request.method == 'POST':
        form = get_mirrorset_definition_form(request, request.POST, instance=mirrorset)

        if mirrorset is not None and request.POST.get('delete', '') == 'delete':
            mirrorset.delete()
            return HttpResponseRedirect(reverse('mirrorsvc:mirrorsets'))

        if form.is_valid():
            new_mirrorset = form.save(commit=False)
            new_mirrorset.owner = request.user
            new_mirrorset.save()
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


def get_tag_definition_form(request, *args, **kwargs):
    form = TagDefinitionForm(*args, **kwargs)
    return form


@login_required
def snapshot_add_tag(request, snapshot_uuid, tag_id):
    snapshot = Snapshot.objects.get(uuid=snapshot_uuid)
    if not snapshot.user_can_modify(request.user):
        return HttpResponse("You don't have access rights to add a tag to this snapshot")

    if tag_id == 'new':
        tag = None
    else:
        tag = Tags.objects.get(pk=tag_id)

    if request.method == 'POST':
        form = get_tag_definition_form(request, request.POST, instance=tag)

        if tag is not None and request.POST.get('delete', '') == 'delete':
            tag.delete()
            return HttpResponseRedirect(reverse('mirrorsvc:snapshots'))

        if form.is_valid():
            new_tag = form.save(commit=False)
            new_tag.snapshot = snapshot
            new_tag.save()
            return HttpResponseRedirect(reverse('mirrorsvc:snapshots'))
    else:
        form = get_tag_definition_form(request, instance=tag)

    return render(request, 'mirrorsvc/html/tag_definition.html',
                  {'form': form, 'snapshot_uuid': snapshot.uuid, 'tag_id': tag_id})


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
                  {'snapshots': snapshots, 'mirrorset': mirrorset})


@login_required
def refresh_mirror_with_uuid(request, mirror_uuid):
    mirror = Mirror.objects.get(uuid=mirror_uuid)
    if mirror.user_can_modify(request.user):
        mirror.schedule_update_mirror()
    return HttpResponseRedirect(reverse('mirrorsvc:mirrors'))


@login_required
def create_new_snapshot(request, uuid):
    ms = MirrorSet.objects.get(uuid=uuid)
    if ms.user_can_modify(request.user):
        snap = Snapshot.objects.create(mirrorset=ms)
        snap.perform_snapshot()
    return HttpResponseRedirect(reverse('mirrorsvc:mirrorset_snapshots', kwargs={'uuid': uuid}))
