from django.conf.urls import include, url

urlpatterns = [
    url(r'^sources/(?P<source_id>\d+|new)/', 'overcast.django.apps.buildsvc.views.package_source', name='package_source'),
    url(r'^sources/', 'overcast.django.apps.buildsvc.views.sources', name='sources'),
    url(r'^repositories/', 'overcast.django.apps.buildsvc.views.repositories', name='repositories'),
    url(r'^builds/', 'overcast.django.apps.buildsvc.views.builds', name='builds'),
]
