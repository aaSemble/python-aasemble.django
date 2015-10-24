from django.test import TestCase, override_settings

@override_settings(BUILDSVC_REPODRIVER='aasemble.django.apps.buildsvc.models.FakeDriver')
class AasembleTestCase(TestCase):
    pass
