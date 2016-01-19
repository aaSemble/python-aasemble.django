import os
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
from aasemble.django.utils import run_cmd

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
    def test_run_cmd_dead_simple(self):
        # Should simply return successfully
        stdout = run_cmd(['true'])
        self.assertEquals(stdout, b'')

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
