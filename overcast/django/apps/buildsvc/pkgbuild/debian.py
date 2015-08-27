import os.path
import debian.deb822

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

    @property
    def package_name(self):
        ctrl = debian.deb822.Deb822(open(os.path.join(self.builddir, 'debian/control'), 'r'))
        return ctrl['Source']

    def populate_debian_dir(self):
        pass

PackageBuilderRegistry.register_builder(DebianBuilder)
