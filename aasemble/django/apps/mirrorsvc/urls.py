from django.conf.urls import include, url

urlpatterns = [
    url(r'^mirrors/', 'aasemble.django.apps.mirrorsvc.views.mirrors', name='mirrors'),
]
