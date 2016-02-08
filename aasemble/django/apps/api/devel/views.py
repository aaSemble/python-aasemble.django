from aasemble.django.apps.api.v3.views import aaSembleV3Views

from . import serializers as serializers_


class aaSembleDevelViews(aaSembleV3Views):
    view_prefix = 'devel'
    serializers = serializers_.aaSembleAPIDevelSerializers()
