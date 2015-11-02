from django.conf.urls import include, url

import aasemble.django.apps.buildsvc.views

urlpatterns = [
    url(r'^sources/(?P<source_id>\d+|new)/', aasemble.django.apps.buildsvc.views.package_source, name='package_source'),
    url(r'^sources/', aasemble.django.apps.buildsvc.views.sources, name='sources'),
    url(r'^repositories/', aasemble.django.apps.buildsvc.views.repositories, name='repositories'),
    url(r'^builds/', aasemble.django.apps.buildsvc.views.builds, name='builds'),
]
