import os.path
import yaml

from aasemble.django.apps.buildsvc.pkgbuild import PackageBuilder, PackageBuilderRegistry
from aasemble.utils import run_cmd
from django.template.loader import render_to_string


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

        return out.decode()

    @property
    def native_version(self):
        return self.retry_if_has_newlines(['python', 'setup.py', '--version'],
                                          logger=self.logger)

    @property
    def package_name(self):
        return self.retry_if_has_newlines(['python', 'setup.py', '--name'],
                                          logger=self.logger)

    @property
    def binary_pkg_name(self):
        pkgname = self.package_name
        if pkgname.startswith('python-'):
            return pkgname
        elif pkgname.endswith('-python'):
            pkgname = pkgname[:-len('-python')]

        return 'python-%s' % (pkgname,)

    def get_pydist_overrides(self):
        return self.get_aasemble_config().get('pydist_override', {})

    def add_pydist_overrides(self):
        pkglist = self.get_pydist_overrides()
        if len(pkglist) == 0:
            self.logger.info('No pydist-overrides in config')
            return
        pydist_overrides = os.path.join(self.builddir, 'debian', 'pydist-overrides')
        pydist_overrides_str = render_to_string(os.path.join(os.path.dirname(__file__), '../templates/buildsvc/pkgbuild/pydist-overrides.tmpl'),
                                     {'pkglist': pkglist})
        with open(pydist_overrides, 'a') as fp:
            fp.write(pydist_overrides_str)
            self.logger.info('Saving pydist-overrides file: %s' % (pydist_overrides))
            return

    def detect_runtime_dependencies(self):
        return ['${python:Depends}']

    def populate_debian_dir(self):
        super(PythonBuilder, self).populate_debian_dir()
        return self.add_pydist_overrides()

    def detect_build_dependencies(self):
        return ['python-all', 'dh-python', 'python-setuptools', 'python-all-dev'] + super(PythonBuilder, self).detect_build_dependencies()

    def extra_dh_args(self):
        return ' --with python2'

PackageBuilderRegistry.register_builder(PythonBuilder)
