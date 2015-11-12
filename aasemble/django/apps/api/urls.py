from django.conf import settings
from django.conf.urls import include, url

from rest_framework_nested import routers

from . import views
from .v1 import views as views_v1
from .v2 import views as views_v2

v1_router = routers.DefaultRouter()
v1_router.register(r'repositories', views_v1.RepositoryViewSet, base_name='v1_repository')
v1_router.register(r'external_dependencies', views_v1.ExternalDependencyViewSet, base_name='v1_externaldependency')
v1_router.register(r'sources', views_v1.PackageSourceViewSet, base_name='v1_packagesource')
v1_router.register(r'builds', views_v1.BuildViewSet, base_name='v1_buildrecord')
v1_router.register(r'mirrors', views_v1.MirrorViewSet, base_name='v1_mirror')
v1_router.register(r'mirror_sets', views_v1.MirrorSetViewSet, base_name='v1_mirrorset')
v1_router.register(r'snapshots', views_v1.SnapshotViewSet, base_name='v1_snapshot')

v1_source_router = routers.NestedSimpleRouter(v1_router, r'sources', lookup='source')
v1_source_router.register(r'builds', views_v1.BuildViewSet, base_name='v1_build')

v1_repository_router = routers.NestedSimpleRouter(v1_router, r'repositories', lookup='repository')
v1_repository_router.register(r'sources', views_v1.PackageSourceViewSet, base_name='v1_packagesource')
v1_repository_router.register(r'external_dependencies', views_v1.ExternalDependencyViewSet, base_name='v1_externaldependency')

v2_router = routers.DefaultRouter()
v2_router.register(r'repositories', views_v2.RepositoryViewSet, base_name='v2_repository')
v2_router.register(r'external_dependencies', views_v2.ExternalDependencyViewSet, base_name='v2_externaldependency')
v2_router.register(r'sources', views_v2.PackageSourceViewSet, base_name='v2_packagesource')
v2_router.register(r'builds', views_v2.BuildViewSet, base_name='v2_buildrecord')
v2_router.register(r'mirrors', views_v2.MirrorViewSet, base_name='v2_mirror')
v2_router.register(r'mirror_sets', views_v2.MirrorSetViewSet, base_name='v2_mirrorset')
v2_router.register(r'snapshots', views_v2.SnapshotViewSet, base_name='v2_snapshot')

v2_source_router = routers.NestedSimpleRouter(v2_router, r'sources', lookup='source')
v2_source_router.register(r'builds', views_v2.BuildViewSet, base_name='v2_build')

v2_repository_router = routers.NestedSimpleRouter(v2_router, r'repositories', lookup='repository')
v2_repository_router.register(r'sources', views_v2.PackageSourceViewSet, base_name='v2_packagesource')
v2_repository_router.register(r'external_dependencies', views_v2.ExternalDependencyViewSet, base_name='v2_externaldependency')


urlpatterns = [
    url(r'^events/github/', views.GithubHookView.as_view()),
    url(r'^v1/', include(v1_router.urls)),
    url(r'^v1/', include(v1_repository_router.urls)),
    url(r'^v1/', include(v1_source_router.urls)),
    url(r'^v1/auth/', include('rest_auth.urls')),
    url(r'^v1/auth/github/$', views_v1.GithubLogin.as_view(), name='github_login'),
    url(r'^v2/', include(v2_router.urls)),
    url(r'^v2/', include(v2_repository_router.urls)),
    url(r'^v2/', include(v2_source_router.urls)),
    url(r'^v2/auth/', include('rest_auth.urls')),
    url(r'^v2/auth/github/$', views_v2.GithubLogin.as_view(), name='github_login'),
]

if getattr(settings, 'SIGNUP_OPEN', False):
    urlpatterns += [url(r'^v1/auth/registration/', include('rest_auth.registration.urls'))]
