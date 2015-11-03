from django.conf.urls import include, url
from django.conf import settings

from rest_framework_nested import routers

from .v1 import views as views_v1

v1_router = routers.DefaultRouter()
v1_router.register(r'repositories', views_v1.RepositoryViewSet)
v1_router.register(r'external_dependencies', views_v1.ExternalDependencyViewSet, base_name='externaldependency')
v1_router.register(r'sources', views_v1.PackageSourceViewSet, base_name='packagesource')
v1_router.register(r'builds', views_v1.BuildViewSet, base_name='buildrecord')
v1_router.register(r'mirrors', views_v1.MirrorViewSet, base_name='mirror')
v1_router.register(r'mirror_sets', views_v1.MirrorSetViewSet, base_name='mirrorset')
v1_router.register(r'snapshots', views_v1.SnapshotViewSet, base_name='snapshot')

v1_source_router = routers.NestedSimpleRouter(v1_router, r'sources', lookup='source')
v1_source_router.register(r'builds', views_v1.BuildViewSet, base_name='build')

v1_repository_router = routers.NestedSimpleRouter(v1_router, r'repositories', lookup='repository')
v1_repository_router.register(r'sources', views_v1.PackageSourceViewSet, base_name='packagesource')
v1_repository_router.register(r'external_dependencies', views_v1.ExternalDependencyViewSet, base_name='externaldependency')

urlpatterns = [
    url(r'^v1/', include(v1_router.urls)),
    url(r'^v1/', include(v1_repository_router.urls)),
    url(r'^v1/', include(v1_source_router.urls)),
    url(r'^v1/auth/', include('rest_auth.urls')),
    url(r'^v1/auth/github/$', views_v1.GithubLogin.as_view(), name='github_login'),
] 

if getattr(settings, 'SIGNUP_OPEN', False):
    urlpatterns += [url(r'^v1/auth/registration/', include('rest_auth.registration.urls'))]
