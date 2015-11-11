import os.path

from ..pkgbuild import PackageBuilder, PackageBuilderRegistry
from ....utils import run_cmd


class PythonBuilder(PackageBuilder):
    @classmethod
    def is_suitable(cls, path):
        return os.path.exists(os.path.join(path, 'setup.py'))

    def retry_if_has_newlines(self, cmd, logger):
        """Sometimes the first run will have noise in it"""
        def run_it():
            return run_cmd(cmd, cwd=self.builddir, discard_stderr=True, logger=logger).strip()

        out = run_it()

        if '\n' in out:
            out = run_it()

        return out

    @property
    def native_version(self):
        return self.retry_if_has_newlines(['python', 'setup.py', '--version'],
                                          logger=self.build_record.logger)

    @property
    def package_name(self):
        return self.retry_if_has_newlines(['python', 'setup.py', '--name'],
                                          logger=self.build_record.logger)

    @property
    def binary_pkg_name(self):
        pkgname = self.package_name
        if pkgname.startswith('python-'):
            return pkgname
        elif pkgname.endswith('-python'):
            pkgname = pkgname[:-len('-python')]

        return 'python-%s' % (pkgname,)

    def detect_runtime_dependencies(self):
        return ['${python:Depends}']

    def detect_build_dependencies(self):
        return ['python-all', 'dh-python', 'python-setuptools', 'python-all-dev'] + super(PythonBuilder, self).detect_build_dependencies()

    def extra_dh_args(self):
        return ' --with python2'

PackageBuilderRegistry.register_builder(PythonBuilder)
