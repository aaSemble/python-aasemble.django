from django.conf.urls import include, url

from rest_framework_nested import routers

from overcast.django.apps.buildsvc import views

router = routers.SimpleRouter()
router.register(r'repositories', views.RepositoryViewSet)
router.register(r'series', views.SeriesViewSet)

repository_router = routers.NestedSimpleRouter(router, r'repositories', lookup='repository')
repository_router.register(r'series', views.SeriesViewSet)

urlpatterns = [
    url(r'^v1/', include(router.urls)),
    url(r'^v1/', include(repository_router.urls)),
] 
