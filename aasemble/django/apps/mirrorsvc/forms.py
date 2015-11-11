from django.forms import ModelForm

from aasemble.django.apps.mirrorsvc.models import Mirror


class MirrorDefinitionForm(ModelForm):
    class Meta:
        model = Mirror
        fields = ['url', 'series', 'components', 'public']
