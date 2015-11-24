from rest_framework import filters

from aasemble.django.apps.api.v2.views import aaSembleV2Views

from . import serializers as serializers_

class aaSembleV3Views(aaSembleV2Views):
    view_prefix = 'v3'
    serializers = serializers_.aaSembleAPIv3Serializers()
