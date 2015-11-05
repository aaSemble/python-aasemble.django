from __future__ import absolute_import

import os.path
import debian.deb822

from ....utils import run_cmd
from ..pkgbuild import PackageBuilder, PackageBuilderRegistry


class DebianBuilder(PackageBuilder):
    @classmethod
    def is_suitable(cls, path):
        return os.path.isdir(os.path.join(path, 'debian'))

    @property
    def native_version(self):
        cmd = ['dpkg-parsechangelog', '--show-field', 'Version']
        v = run_cmd(cmd, cwd=self.builddir).strip()
        if ':' in v:
            v = v.split(':')[1]
        if '-' in v:
            v = v.split('-')[0]
        return v

    @property
    def package_name(self):
        ctrl = debian.deb822.Deb822(open(os.path.join(self.builddir, 'debian/control'), 'r'))
        return ctrl['Source']

    def populate_debian_dir(self):
        pass

PackageBuilderRegistry.register_builder(DebianBuilder)
