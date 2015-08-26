from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'overcast.django.apps.main.views.index', name='index'),
    url(r'^buildsvc/', include('overcast.django.apps.buildsvc.urls', namespace='buildsvc')),
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='logout'),
    url('', include('social.apps.django_app.urls', namespace='social'))
]
