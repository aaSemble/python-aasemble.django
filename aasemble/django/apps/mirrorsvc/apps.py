from django.apps import AppConfig


class MirrorServiceConfig(AppConfig):
    name = 'aasemble.django.apps.mirrorsvc'

    def ready(self):
        from . import checks  # noqa
