import os.path

from ..utils import run_cmd, recursive_render
from ..pkgbuild import PackageBuilder, PackageBuilderRegistry

class PythonBuilder(PackageBuilder):
    @classmethod
    def is_suitable(cls, path):
        return os.path.exists(os.path.join(path, 'setup.py'))

    @property
    def native_version(self):
        cmd = ['python', 'setup.py', '--version']
        return run_cmd(cmd, cwd=self.builddir, discard_stderr=True).strip()

    @property
    def package_name(self):
        cmd = ['python', 'setup.py', '--name']
        return run_cmd(cmd, cwd=self.builddir, discard_stderr=True).strip()

    def detect_runtime_dependencies(self):
        return ['${python:Depends}']

    def detect_build_dependencies(self):
        return ['python-all', 'dh-python', 'python-setuptools']

    def extra_dh_args(self):
        return ' --with python2'
    
PackageBuilderRegistry.register_builder(PythonBuilder)
