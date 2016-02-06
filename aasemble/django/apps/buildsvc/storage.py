from django.conf import settings
from django.core.files.storage import FileSystemStorage


class Storage(object):
    def __init__(self, django_storage):
        self.django_storage = django_storage

    def exists(self, *args, **kwargs):
        return self.django_storage.exists(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.django_storage.delete(*args, **kwargs)

    def save(self, path, *args, **kwargs):
        if kwargs.pop('overwrite', False):
            self.delete(path)
        return self.django_storage.save(path, *args, **kwargs)


def get_repository_storage_driver():
    return Storage(FileSystemStorage(location=settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR))
