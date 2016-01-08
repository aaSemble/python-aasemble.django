from aasemble.django.apps.api.v2 import serializers as v2_serializers


class aaSembleAPIv3Serializers(v2_serializers.aaSembleAPIv2Serializers):
    view_prefix = 'v3'
    builds_nest_source = True
    include_build_duration = True
    include_key_data_link = True
    include_builds_link = True
    include_sources_list_in_mirrorset = True
    include_sources_list_in_mirrors = True
