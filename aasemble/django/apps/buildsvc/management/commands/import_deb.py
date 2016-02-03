from django.core.management.base import BaseCommand

from aasemble.django.apps.buildsvc.models import Repository
from aasemble.django.apps.buildsvc.models.binary_package_version import BinaryPackageVersion


class Command(BaseCommand):
    help = 'Imports binary package into database'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str)
        parser.add_argument('user', type=str)
        parser.add_argument('repository', type=str)

    def handle(self, *args, **options):
        repository = Repository.objects.get(user__username=options['user'], name=options['repository'])
        BinaryPackageVersion.import_file(repository.first_series(), options['path'])
        repository.export()
