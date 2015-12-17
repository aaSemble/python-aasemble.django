from django.forms import ModelForm

from aasemble.django.apps.buildsvc.models import ExternalDependency, PackageSource


class PackageSourceForm(ModelForm):
    class Meta:
        model = PackageSource
        fields = ['git_url', 'branch', 'series']


class ExternalDependencyForm(ModelForm):
    class Meta:
        model = ExternalDependency
        fields = ['url', 'series', 'components', 'own_series', 'key']
