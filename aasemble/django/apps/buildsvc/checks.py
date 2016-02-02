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

E003 = Error(
    "You do not seem to have reprepro installed",
    id='aasemble.buildsvc.E003',
)

E004 = Error(
    "You have specified GCENode as your executor, but have not set "
    "AASEMBLE_BUILDSVC_GCE_KEY_FILE.",
    id='aasemble.buildsvc.E004',
)

E005 = Error(
    "The file provided as AASEMBLE_BUILDSVC_GCE_KEY_FILE is not readable",
    id='aasemble.buildsvc.E004',
)

W001 = Error(
    "You have not configured allauth to request access to user's e-mails. "
    "Depending on your authentication config, this may be a problem.",
    id='aasemble.W001',
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


@register(deploy=True)
def reprepro_available(app_configs, **kwargs):
    for d in os.environ['PATH'].split(':'):
        if os.access(os.path.join(d, 'reprepro'), os.X_OK):
            return []
    return [E003]


@register(deploy=True)
def github_email_scope(app_configs, **kwargs):
    if 'user:email' in getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}).get('github', {}).get('SCOPE', []):
        return []
    return [W001]


@register(deploy=True)
def gce_config_complete(app_configs, **kwargs):
    if getattr(settings, 'AASEMBLE_BUILDSVC_EXECUTOR') == 'GCENode':
        if not hasattr(settings, 'AASEMBLE_BUILDSVC_GCE_KEY_FILE'):
            return [E004]
        elif not os.access(settings.AASEMBLE_BUILDSVC_GCE_KEY_FILE, os.R_OK):
            return [E005]
    return []
