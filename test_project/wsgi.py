"""
WSGI config for www project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os
import os.path
import sys

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from dj_static import Cling
from urlparse import urlparse

APT_BASE_URL_PATH = urlparse(settings.BUILDSVC_REPOS_BASE_URL).path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

class AptCling(Cling):
    def get_base_url(self):
        return APT_BASE_URL_PATH

    def _should_handle(self, *args, **kwargs):
        return super(AptCling, self)._should_handle(*args, **kwargs)

application = AptCling(Cling(get_wsgi_application()), base_dir=settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR, ignore_debug=True)
