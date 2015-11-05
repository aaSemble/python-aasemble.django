from django.apps import AppConfig


class APIConfig(AppConfig):
    name = 'aasemble.django.apps.api'

    def ready(self):
        from . import signals  # noqa
