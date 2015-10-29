from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^api/', include('aasemble.django.apps.api.urls')),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^profile/$', 'aasemble.django.apps.main.views.profile', name='profile'),
    url(r'^$', 'aasemble.django.apps.main.views.index', name='index'),
    url(r'^buildsvc/', include('aasemble.django.apps.buildsvc.urls', namespace='buildsvc')),
    url(r'^mirrorsvc/', include('aasemble.django.apps.mirrorsvc.urls', namespace='mirrorsvc')),
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='logout'),
]
