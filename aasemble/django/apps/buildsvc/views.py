import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .forms import ExternalDependencyForm, PackageSourceForm
from .models import BuildRecord, ExternalDependency, PackageSource, Repository, Series

LOG = logging.getLogger(__name__)


def get_package_source_form(request, *args, **kwargs):
    form = PackageSourceForm(*args, **kwargs)

    sqs = Series.objects.filter(repository__in=Repository.lookup_by_user(request.user))

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

        if ((form.is_valid() and
             form.cleaned_data['series'].user_can_modify(request.user))):
            ps = form.save()
            ps.register_webhook()
            return HttpResponseRedirect(reverse('buildsvc:sources'))
    else:
        form = get_package_source_form(request, instance=ps)

    return render(request, 'buildsvc/html/package_source.html',
                  {'form': form, 'source_id': source_id})


def get_external_dependency_form(request, *args, **kwargs):
    form = ExternalDependencyForm(*args, **kwargs)

    return form


@login_required
def external_dependency(request, dependency_uuid):
    if dependency_uuid == 'new':
        dependency = None
    else:
        dependency = ExternalDependency.objects.get(uuid=dependency_uuid)
        if not dependency.user_can_modify(request.user):
            dependency, dependency_uuid = None, 'new'

    if request.method == 'POST':
        form = get_external_dependency_form(request, request.POST, instance=dependency)

        if dependency is not None and request.POST.get('delete', '') == 'delete':
            dependency.delete()
            return HttpResponseRedirect(reverse('buildsvc:external_dependencies'))

        if ((form.is_valid() and
             form.cleaned_data['own_series'].user_can_modify(request.user))):
            form.save()
            return HttpResponseRedirect(reverse('buildsvc:external_dependencies'))
    else:
        form = get_external_dependency_form(request, instance=dependency)

    return render(request, 'buildsvc/html/external_dependency_definition.html',
                  {'form': form, 'dependency_uuid': dependency_uuid})


@login_required
def enable_source_repo(request, source_id):
    try:
        ps = PackageSource.objects.get(id=source_id)
        if ps.user_can_modify(request.user):
            ps.disabled = False
            ps.save()
    except ObjectDoesNotExist:
        LOG.debug('Could not find source repo with source_id %s. Repo still disabled.' % source_id)

    return HttpResponseRedirect(reverse('buildsvc:sources'))


@login_required
def sources(request):
    sources = PackageSource.objects.filter(series__repository__in=Repository.lookup_by_user(request.user))
    return render(request, 'buildsvc/html/sources.html', {'sources': sources})


@login_required
def builds(request):
    builds = BuildRecord.objects.filter(source__series__repository__in=Repository.lookup_by_user(request.user)).order_by('-build_started')
    return render(request, 'buildsvc/html/builds.html', {'builds': builds})


@login_required
def rebuild(request, source_id):
    ps = PackageSource.objects.get(pk=source_id)
    if ps.series.user_can_modify(request.user):
        try:
            ps.build()
        except Exception:
            # will handle it later
            pass
        return render(request, 'buildsvc/html/rebuild.html', {'source': ps})
    else:
        return HttpResponseRedirect(reverse('buildsvc:sources'))


@login_required
def repositories(request):
    repositories = Repository.lookup_by_user(request.user)
    return render(request, 'buildsvc/html/repositories.html',
                  {'repositories': repositories, 'settings': settings})


@login_required
def external_dependencies(request):
    dependencies = ExternalDependency.lookup_by_user(request.user)
    return render(request, 'buildsvc/html/external_dependencies.html', {'dependencies': dependencies})
