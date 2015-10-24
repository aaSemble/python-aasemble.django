from django.apps import AppConfig

class BuildServiceConfig(AppConfig):
    name = 'aasemble.django.apps.buildsvc'
    def ready(self):
        from . import signals
