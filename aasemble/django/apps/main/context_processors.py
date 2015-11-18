from test_project import settings


def internal_name_change(request):
    title = getattr(settings, 'AASEMBLE_OVERRIDE_NAME', 'aaSemble')
    return {'title': title}
