from django.conf.urls import url

import aasemble.django.apps.buildsvc.views

urlpatterns = [
    url(r'^sources/(?P<source_id>\d+)/enable/', aasemble.django.apps.buildsvc.views.enable_source_repo, name='enable_source_repo'),
    url(r'^sources/(?P<source_id>\d+|new)/', aasemble.django.apps.buildsvc.views.package_source, name='package_source'),
    url(r'^sources/', aasemble.django.apps.buildsvc.views.sources, name='sources'),
    url(r'^repositories/', aasemble.django.apps.buildsvc.views.repositories, name='repositories'),
    url(r'^builds/rebuild/(?P<source_id>\d+)/', aasemble.django.apps.buildsvc.views.rebuild, name='rebuild'),
    url(r'^builds/', aasemble.django.apps.buildsvc.views.builds, name='builds'),
    url(r'^external_dependencies/(?P<dependency_uuid>[^/]+|new)/$', aasemble.django.apps.buildsvc.views.external_dependency, name='dependency_definition'),
    url(r'^external_dependencies/', aasemble.django.apps.buildsvc.views.external_dependencies, name='external_dependencies'),
]
