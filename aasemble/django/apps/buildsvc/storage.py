from django.conf import settings
from django.core.files.storage import FileSystemStorage


def get_repository_storage_driver():
    return FileSystemStorage(location=settings.BUILDSVC_REPOS_BASE_PUBLIC_DIR)
