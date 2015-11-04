from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
import django.db.utils
from django.forms import ModelChoiceField
from django.http import HttpResponseRedirect
from django.shortcuts import render

from rest_framework import viewsets
from .serializers import UserSerializer, GroupSerializer, RepositorySerializer, SeriesSerializer, PackageSourceSerializer, ExternalDependencySerializer, BuildRecordSerializer
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


#############
# API stuff #
#############

class RepositoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows repositories to be viewed or edited.
    """
    queryset = Repository.objects.all()

    def get_queryset(self):
        return Repository.lookup_by_user(self.request.user)

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except django.db.utils.IntegrityError as e:
            raise DuplicateResourceException()

    serializer_class = RepositorySerializer


class SeriesViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows series to be viewed or edited.
    """
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer

    def get_queryset(self):
        return self.queryset.filter(repository=Repository.lookup_by_user(self.request.user))


class PackageSourceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows series to be viewed or edited.
    """
    queryset = PackageSource.objects.all()
    serializer_class = PackageSourceSerializer

    def get_queryset(self):
        qs = self.queryset.filter(series__repository__in=Repository.lookup_by_user(self.request.user))
        if hasattr(self, 'request') and hasattr(self.request, 'resolver_match'):
            fn, args, kwargs = self.request.resolver_match
            if 'repository_pk' in kwargs:
                qs = qs.filter(series__repository=kwargs['repository_pk'])

        return qs


class ExternalDependencyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows external dependencies to be viewed or edited.
    """
    queryset = ExternalDependency.objects.all()
    serializer_class = ExternalDependencySerializer


    def get_queryset(self):
        qs = self.queryset.filter(own_series__repository__in=Repository.lookup_by_user(self.request.user))
        if hasattr(self, 'request') and hasattr(self.request, 'resolver_match'):
            fn, args, kwargs = self.request.resolver_match
            if 'repository_pk' in kwargs:
                qs = qs.filter(own_series__repository=kwargs['repository_pk'])

        return qs


class BuildViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows builds viewed
    """
    queryset = BuildRecord.objects.all()
    serializer_class = BuildRecordSerializer

    def get_queryset(self):
        qs = self.queryset.filter(source__series__repository__in=Repository.lookup_by_user(self.request.user))
        if hasattr(self, 'request') and hasattr(self.request, 'resolver_match'):
            fn, args, kwargs = self.request.resolver_match
            if 'source_pk' in kwargs:
                qs = qs.filter(source=kwargs['source_pk'])

        return qs
