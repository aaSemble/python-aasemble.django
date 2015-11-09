import os

from django.conf import settings
from django.core.checks import Error, register

E001 = Error(
    "You do not have write and execute access to BUILDSVC_REPOS_BASE_PUBLIC_DIR",
    id='aasemble.buildsvc.E001',
)

E002 = Error(
    "You do not have write and execute access to BUILDSVC_REPOS_BASE_DIR",
    id='aasemble.buildsvc.E002',
)

@register(deploy=True)
def public_dir_writable(app_configs, **kwargs):
    if ((os.access(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR, os.W_OK) and
         os.access(settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR, os.X_OK))):
        return []
    return [E001]

@register(deploy=True)
def private_dir_writable(app_configs, **kwargs):
    if ((os.access(settings.BUILDSVC_REPOS_BASE_DIR, os.W_OK) and
         os.access(settings.BUILDSVC_REPOS_BASE_DIR, os.X_OK))):
        return []
    return [E002]
