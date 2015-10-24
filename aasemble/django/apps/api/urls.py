from django.conf.urls import include, url
from django.conf import settings

from rest_framework_nested import routers

from aasemble.django.apps.buildsvc import views as build_views
from aasemble.django.apps.mirrorsvc import views as mirror_views
from aasemble.django.apps.api.views import GithubLogin

router = routers.DefaultRouter()
router.register(r'repositories', build_views.RepositoryViewSet)
router.register(r'external_dependencies', build_views.ExternalDependencyViewSet, base_name='externaldependency')
router.register(r'sources', build_views.PackageSourceViewSet, base_name='packagesource')
router.register(r'builds', build_views.BuildViewSet, base_name='buildrecord')
router.register(r'mirrors', mirror_views.MirrorViewSet, base_name='mirror')
router.register(r'mirror_sets', mirror_views.MirrorSetViewSet, base_name='mirrorset')
router.register(r'snapshots', mirror_views.SnapshotViewSet, base_name='snapshot')

source_router = routers.NestedSimpleRouter(router, r'sources', lookup='source')
source_router.register(r'builds', build_views.BuildViewSet, base_name='build')

repository_router = routers.NestedSimpleRouter(router, r'repositories', lookup='repository')
repository_router.register(r'sources', build_views.PackageSourceViewSet, base_name='packagesource')
repository_router.register(r'external_dependencies', build_views.ExternalDependencyViewSet, base_name='externaldependency')

urlpatterns = [
    url(r'^v1/', include(router.urls)),
    url(r'^v1/', include(repository_router.urls)),
    url(r'^v1/', include(source_router.urls)),
    url(r'^v1/auth/', include('rest_auth.urls')),
    url(r'^v1/auth/github/$', GithubLogin.as_view(), name='github_login')
] 

if getattr(settings, 'SIGNUP_OPEN', False):
    urlpatterns += [url(r'^v1/auth/registration/', include('rest_auth.registration.urls'))]
