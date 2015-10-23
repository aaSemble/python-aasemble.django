from django.test import TestCase, override_settings

@override_settings(BUILDSVC_REPODRIVER='overcast.django.apps.buildsvc.models.FakeDriver')
class OvercastTestCase(TestCase):
    pass
