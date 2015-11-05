from django.conf.urls import include, url

import aasemble.django.apps.mirrorsvc.views

urlpatterns = [
    url(r'^mirrors/', aasemble.django.apps.mirrorsvc.views.mirrors, name='mirrors'),
    url(r'^snapshots/', aasemble.django.apps.mirrorsvc.views.snapshots, name='snapshots'),
    url(r'^mirrorsets/(?P<uuid>[^/]+)/snapshots/', aasemble.django.apps.mirrorsvc.views.mirrorset_snapshots, name='mirrorset_snapshots'),
    url(r'^mirrorsets/', aasemble.django.apps.mirrorsvc.views.mirrorsets, name='mirrorsets'),
]
