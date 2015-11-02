from django.conf.urls import include, url

import aasemble.django.apps.mirrorsvc.views

urlpatterns = [
    url(r'^mirrors/', aasemble.django.apps.mirrorsvc.views.mirrors, name='mirrors'),
    url(r'^snapshots/', aasemble.django.apps.mirrorsvc.views.snapshots, name='snapshots'),
]
