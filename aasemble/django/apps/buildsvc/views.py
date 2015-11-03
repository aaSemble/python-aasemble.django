from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
import django.db.utils
from django.forms import ModelChoiceField
from django.http import HttpResponseRedirect
from django.shortcuts import render

from rest_framework import viewsets
from .models import BuildRecord, Repository, PackageSource, PackageSourceForm, Series, GithubRepository, ExternalDependency

from aasemble.django.exceptions import DuplicateResourceException

def get_package_source_form(request, *args, **kwargs):
    form = PackageSourceForm(*args, **kwargs)

    sqs = (Series.objects.filter(repository__user=request.user) |
           Series.objects.filter(repository__extra_admins=request.user.groups.all()))

    form.fields['series'].queryset = sqs

    return form

@login_required
def package_source(request, source_id):
    if source_id == 'new':
        ps = None
    else:
        ps = PackageSource.objects.get(pk=source_id)
        if not ps.series.user_can_modify(request.user):
            ps, source_id = None, 'new'

    if request.method == 'POST':
        form = get_package_source_form(request, request.POST, instance=ps)

        if ps is not None and request.POST.get('delete', '') == 'delete':
            ps.delete()
            return HttpResponseRedirect(reverse('buildsvc:sources'))

        if (form.is_valid() and
            form.cleaned_data['series'].user_can_modify(request.user)):
            form.save()
            return HttpResponseRedirect(reverse('buildsvc:sources'))
    else:
        form = get_package_source_form(request, instance=ps)

    return render(request, 'buildsvc/html/package_source.html',
                  {'form': form, 'source_id': source_id})


@login_required
def sources(request):
    sources = PackageSource.objects.filter(series__repository__in=Repository.lookup_by_user(request.user))
    return render(request, 'buildsvc/html/sources.html', {'sources': sources})

@login_required
def builds(request):
    builds = BuildRecord.objects.filter(source__series__repository__in=Repository.lookup_by_user(request.user)).order_by('build_started')
    return render(request, 'buildsvc/html/builds.html', {'builds': builds})

@login_required
def repositories(request):
    repositories = Repository.lookup_by_user(request.user)
    return render(request, 'buildsvc/html/repositories.html',
                  {'repositories': repositories, 'settings': settings})
