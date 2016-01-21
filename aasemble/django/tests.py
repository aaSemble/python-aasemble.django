import os
import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import (
    BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
)
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.test import LiveServerTestCase, TestCase, override_settings

import mock

from aasemble.django.exceptions import CommandFailed
from aasemble.django.utils import ensure_dir, escape_cmd_for_ssh, recursive_render, run_cmd, ssh_get, ssh_run_cmd

stdout_stderr_script = '''#!/bin/sh

echo stdout
echo stderr >&2
'''


@override_settings(BUILDSVC_REPODRIVER='aasemble.django.apps.buildsvc.models.FakeDriver')
class AasembleTestCase(TestCase):
    fixtures = ['complete.json']


class AasembleLiveServerTestCase(LiveServerTestCase):
    fixtures = ['complete.json']


def create_session_cookie(username, password):
    # First, create a new test user
    user = User.objects.create_user(username=username, password=password)

    # Then create the authenticated session using the new user credentials
    session = SessionStore()
    session[SESSION_KEY] = user.pk
    session[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    # Finally, create the cookie dictionary
    cookie = {
        'name': settings.SESSION_COOKIE_NAME,
        'value': session.session_key,
        'secure': False,
        'path': '/',
    }
    return cookie


def create_session_for_given_user(username):
    user = User.objects.get(username=username)
    # Then create the authenticated session using the given credentials
    session = SessionStore()
    session[SESSION_KEY] = user.pk
    session[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    # Finally, create the cookie dictionary
    cookie = {
        'name': settings.SESSION_COOKIE_NAME,
        'value': session.session_key,
        'secure': False,
        'path': '/',
    }
    return cookie


class UtilsTestCase(AasembleTestCase):
    @override_settings(TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates',
                                   'DIRS': [os.path.dirname(__file__)]}])
    def test_recursive_render(self):
        tmpdir = tempfile.mkdtemp()
        try:
            recursive_render(os.path.join(os.path.dirname(__file__),
                                          'test_data', 'recursive_render'),
                             tmpdir, {'var': 'resolvedvar'})
            self.assertFalse(os.path.exists(os.path.join(tmpdir, 'foo', 'bar', '.baz.swp')))

            with open(os.path.join(tmpdir, 'foo', 'bar', 'baz'), 'r') as fp:
                self.assertEquals('resolvedvar\n', fp.read())

            with open(os.path.join(tmpdir, 'wibble'), 'r') as fp:
                self.assertEquals('wobble\n', fp.read())
        finally:
            shutil.rmtree(tmpdir)

    def test_escape_cmd_for_ssh(self):
        self.assertEquals(escape_cmd_for_ssh(['echo', """'%\""""]), 'echo \'\'"\'"\'%"\'')

    @mock.patch('aasemble.django.utils.run_cmd')
    def test_ssh_get(self, run_cmd):
        ssh_get('user@remote', 'foo/bar*', 'mydestdir')
        run_cmd.assert_called_with(['scp',
                                    '-q',
                                    '-oStrictHostKeyChecking=no',
                                    '-oUserKnownHostsFile=/dev/null',
                                    'user@remote:foo/bar*', '.'], cwd='mydestdir')

    @mock.patch('aasemble.django.utils.run_cmd')
    def test_ssh_run_cmd(self, run_cmd):
        ssh_run_cmd('user@remote', ['touch', '"#'])
        run_cmd.assert_called_with(['ssh',
                                    '-q',
                                    '-oStrictHostKeyChecking=no',
                                    '-oUserKnownHostsFile=/dev/null',
                                    'user@remote',
                                    'touch \'"#\''])

    @mock.patch('aasemble.django.utils.run_cmd')
    def test_ssh_run_cmd_with_remote_cwd(self, run_cmd):
        ssh_run_cmd('user@remote', ['touch', '"#'], remote_cwd='workspace')
        run_cmd.assert_called_with(['ssh',
                                    '-q',
                                    '-oStrictHostKeyChecking=no',
                                    '-oUserKnownHostsFile=/dev/null',
                                    'user@remote',
                                    'mkdir -p workspace ; cd workspace ; touch \'"#\''])

    def test_ensure_dir(self):
        tmpdir = tempfile.mkdtemp()
        try:
            testdir = os.path.join(tmpdir, 'testdir')
            self.assertEquals(ensure_dir(testdir), testdir)
            self.assertTrue(os.path.isdir(testdir))
            self.assertEquals(ensure_dir(testdir), testdir)
        finally:
            shutil.rmtree(tmpdir)

    def test_run_cmd_dead_simple(self):
        # Should simply return successfully
        stdout = run_cmd(['true'])
        self.assertEquals(stdout, b'')

    def test_run_cmd_with_input(self):
        stdout = run_cmd(['cat'], input=b'hello\n')
        self.assertEquals(stdout, b'hello\n')

    def test_run_cmd_no_trailing_linefeed(self):
        logger = mock.MagicMock()
        stdout = run_cmd(['bash', '-c', 'echo -n foo'], logger=logger)
        self.assertEquals(stdout, b'foo')
        logger.log.assert_called_with(20, 'foo')

    def test_run_cmd_fail_raises_exception(self):
        self.assertRaises(CommandFailed, run_cmd, ['false'])

    def test_run_cmd_override_env(self):
        os.environ['TESTVAR'] = 'foo'
        stdout = run_cmd(['env'])
        self.assertIn(b'TESTVAR=foo', stdout)

        stdout = run_cmd(['env'], override_env={'TESTVAR': 'bar'})
        self.assertIn(b'TESTVAR=bar', stdout)

        stdout = run_cmd(['env'], override_env={'TESTVAR': None})
        self.assertNotIn(b'TESTVAR=', stdout)

    def test_run_cmd_other_cwd(self):
        self.assertEquals(run_cmd(['pwd'], cwd='/').strip(), b'/')

    def _prepare_stdout_stderr_script(self):
        _fd, tmpfile = tempfile.mkstemp()
        try:
            os.close(_fd)
            with open(tmpfile, 'w') as fp:
                fp.write(stdout_stderr_script)
            os.chmod(tmpfile, 0o0755)
            return tmpfile
        except:  # pragma: nocover
            os.unlink(tmpfile)
            raise

    def test_run_cmd_stdout_includes_stderr(self):
        tmpfile = self._prepare_stdout_stderr_script()
        try:
            self.assertIn(b'stderr', run_cmd([tmpfile]))
        finally:
            os.unlink(tmpfile)

    def test_run_cmd_stdout_can_discard_stderr(self):
        tmpfile = self._prepare_stdout_stderr_script()
        try:
            self.assertNotIn(b'stderr', run_cmd([tmpfile], discard_stderr=True))
        finally:
            os.unlink(tmpfile)

    def test_run_cmd_alternate_stdout(self):
        fd, tmpfile = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'wb') as fp:
                rv = run_cmd(['echo', 'foo'], stdout=fp)

            self.assertEquals(rv, None)

            with open(tmpfile, 'rb') as fp:
                self.assertEquals(fp.read(), b'foo\n')

        finally:
            os.unlink(tmpfile)
