from test_project import settings


def internal_name_change(request):
    try:
        title = settings.AASEMBLE_OVERRIDE_NAME
    except AttributeError:
        title = 'aaSemble'
    # title = getattr(settings, 'AASEMBLE_OVERRIDE_NAME', default='aaSemble')  # This gives TypeError:
    # getattr() takes no keyword arguments
    return {'title': title}
