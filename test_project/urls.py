from django.conf.urls import include, url
from django.contrib import admin

from rest_framework_nested import routers

from overcast.django.apps.buildsvc import views

router = routers.SimpleRouter()
router.register(r'repositories', views.RepositoryViewSet)
router.register(r'series', views.SeriesViewSet)
repository_router = routers.NestedSimpleRouter(router, r'repositories', lookup='repository')
repository_router.register(r'series', views.SeriesViewSet)

urlpatterns = [
    url(r'^api/v1/', include(router.urls)),
    url(r'^api/v1/', include(repository_router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'overcast.django.apps.main.views.index', name='index'),
    url(r'^buildsvc/', include('overcast.django.apps.buildsvc.urls', namespace='buildsvc')),
    url(r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='logout'),
    url('', include('social.apps.django_app.urls', namespace='social'))
]
