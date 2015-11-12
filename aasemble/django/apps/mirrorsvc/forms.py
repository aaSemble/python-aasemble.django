from django.forms import ModelForm

from aasemble.django.apps.mirrorsvc.models import Mirror, MirrorSet


class MirrorDefinitionForm(ModelForm):
    class Meta:
        model = Mirror
        fields = ['url', 'series', 'components', 'public']


class MirrorSetDefinitionForm(ModelForm):
    class Meta:
        model = MirrorSet
        fields = ['name', 'mirrors']
