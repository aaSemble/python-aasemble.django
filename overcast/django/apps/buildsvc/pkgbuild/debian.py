import os.path

from ..utils import run_cmd
from ..pkgbuild import PackageBuilder, PackageBuilderRegistry

class DebianBuilder(PackageBuilder):
    @classmethod
    def is_suitable(cls, path):
        print os.path.join(path, 'debian')
        return os.path.isdir(os.path.join(path, 'debian'))

    @property
    def native_version(self):
        cmd = ['dpkg-parsechangelog', '--show-field', 'Version']
        return run_cmd(cmd, cwd=self.builddir).strip()

    def populate_debian_dir(self):
        pass

PackageBuilderRegistry.register_builder(DebianBuilder)
