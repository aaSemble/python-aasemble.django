from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from rest_framework import viewsets
from .serializers import UserSerializer, GroupSerializer, RepositorySerializer, SeriesSerializer, PackageSourceSerializer


from .models import BuildRecord, Repository, PackageSource, PackageSourceForm, Series, GithubRepository

def get_package_source_form(request, *args, **kwargs):
    form = PackageSourceForm(*args, **kwargs)

    sqs = (Series.objects.filter(repository__user=request.user) |
           Series.objects.filter(repository__extra_admins=request.user.groups.all()))
    grqs = GithubRepository.objects.filter(user=request.user).order_by('repo_owner', 'repo_name')

    form.fields['series'].queryset = sqs
    form.fields['github_repository'].queryset = grqs

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
            form.cleaned_data['series'].user_can_modify(request.user) and
            form.cleaned_data['github_repository'].user == request.user):
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
        return self.queryset.filter(series__repository=Repository.lookup_by_user(self.request.user))

