from django.apps import AppConfig

class APIConfig(AppConfig):
    name = 'overcast.django.apps.api'
    def ready(self):
        from . import signals
