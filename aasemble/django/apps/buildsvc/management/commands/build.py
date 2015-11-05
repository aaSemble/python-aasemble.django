from django.core.management.base import BaseCommand

from ...pkgbuild import choose_builder
from ...models import PackageSource


class Command(BaseCommand):
    help = 'Generates a source package given package source'

    def add_arguments(self, parser):
        parser.add_argument('id', type=int)

    def handle(self, *args, **options):
        ps = PackageSource.objects.get(id=options['id'])
        tmpdir, builddir, sha = ps.checkout()
        builder_cls = choose_builder(builddir)
        print 'Building with', builder_cls
        builder = builder_cls(tmpdir, ps, build_counter=ps.build_counter + 1, save_build_record=False)
        builder.build()
