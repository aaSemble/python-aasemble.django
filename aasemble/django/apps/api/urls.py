from django.conf.urls import include, url

from . import views
from .v1 import views as views_v1
from .v2 import views as views_v2
from .v3 import views as views_v3

urlpatterns = [
    url(r'^events/github/', views.GithubHookView.as_view()),
    url(r'^v1/', include(views_v1.aaSembleV1Views().urls)),
    url(r'^v2/', include(views_v2.aaSembleV2Views().urls)),
    url(r'^v3/', include(views_v3.aaSembleV3Views().urls)),
]
