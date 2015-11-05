import os.path

from ..pkgbuild import PackageBuilder, PackageBuilderRegistry


class GolangBuilder(PackageBuilder):
    def detect_build_dependencies(self):
        return ['golang-go'] + super(GolangBuilder, self).detect_build_dependencies()

    @classmethod
    def is_suitable(cls, path):
        for root, dirs, files in os.walk(path):
            if any([f.endswith('.go') for f in files]):
                return True
        return False


PackageBuilderRegistry.register_builder(GolangBuilder)
