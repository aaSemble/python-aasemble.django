from django.conf.urls import url

import aasemble.django.apps.mirrorsvc.views

urlpatterns = [
    url(r'^mirrors/(?P<mirror_id>\d+|new)/', aasemble.django.apps.mirrorsvc.views.mirror_definition,
        name='mirror_definition'),  # Added before mirrors/ to override next line
    url(r'^mirrors/', aasemble.django.apps.mirrorsvc.views.mirrors, name='mirrors'),
    url(r'^snapshots/', aasemble.django.apps.mirrorsvc.views.snapshots, name='snapshots'),
    url(r'^mirrorsets/(?P<uuid>[^/]+)/snapshots/', aasemble.django.apps.mirrorsvc.views.mirrorset_snapshots, name='mirrorset_snapshots'),
    url(r'^mirrorsets/', aasemble.django.apps.mirrorsvc.views.mirrorsets, name='mirrorsets'),
]
