from django.forms import ModelForm

from aasemble.django.apps.mirrorsvc.models import Mirror, MirrorSet, Tags


class MirrorDefinitionForm(ModelForm):
    class Meta:
        model = Mirror
        fields = ['url', 'series', 'components', 'public']


class MirrorSetDefinitionForm(ModelForm):
    class Meta:
        model = MirrorSet
        fields = ['name', 'mirrors']


class TagDefinitionForm(ModelForm):
    class Meta:
        model = Tags
        fields = ['tag']
