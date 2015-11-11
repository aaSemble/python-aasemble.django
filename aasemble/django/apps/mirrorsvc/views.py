from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from .models import Mirror, MirrorSet, Snapshot
from .forms import MirrorDefinitionForm


def get_mirror_definition_form(request, *args, **kwargs):
    form = MirrorDefinitionForm(*args, **kwargs)
    return form


@login_required
def mirror_definition(request, mirror_id):
    # print("entered mirror_definition function")
    if mirror_id == 'new':
        print("mirror_id==new")
        mirror = None
    else:
        mirror = Mirror.objects.get(pk=mirror_id)
        if not mirror.user_can_modify(request.user):
            mirror, mirror_id = None, 'new'

    if request.method == 'POST':
        print("Entered request.method == POST")
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
                  {'form': form, 'mirror_id': mirror_id})


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
