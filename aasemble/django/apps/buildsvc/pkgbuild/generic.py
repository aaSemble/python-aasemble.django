from ..pkgbuild import PackageBuilder, PackageBuilderRegistry


class GenericBuilder(PackageBuilder):
    @classmethod
    def is_suitable(cls, path):
        return True


PackageBuilderRegistry.register_builder(GenericBuilder)
