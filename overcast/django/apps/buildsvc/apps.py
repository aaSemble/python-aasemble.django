from django.apps import AppConfig

class BuildServiceConfig(AppConfig):
    name = 'overcast.django.apps.buildsvc'
    def ready(self):
        import signals
