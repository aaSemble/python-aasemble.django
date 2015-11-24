from aasemble.django.apps.api.v1 import serializers as v1_serializers


class aaSembleAPIv2Serializers(v1_serializers.aaSembleAPIv1Serializers):
    view_prefix = 'v2'
    default_lookup_field = 'uuid'
    snapshots_have_tags = True
