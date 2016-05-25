from aasemble.django.apps.api.v3 import serializers as v3_serializers


class aaSembleAPIDevelSerializers(v3_serializers.aaSembleAPIv3Serializers):
    view_prefix = 'devel'
    has_nodes = True
