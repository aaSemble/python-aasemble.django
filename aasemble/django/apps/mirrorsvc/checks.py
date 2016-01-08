import os

from django.core.checks import Error, register

E001 = Error(
    "You do not seem to have reprepro installed",
    id='aasemble.mirrorsvc.E001',
)


@register(deploy=True)
def reprepro_available(app_configs, **kwargs):
    for d in os.environ['PATH'].split(':'):
        if os.access(os.path.join(d, 'apt-mirror'), os.X_OK):
            return []
    return [E001]
