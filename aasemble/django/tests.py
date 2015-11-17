import os
import tempfile

from django.conf import settings
from django.contrib.auth import (
    BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
)
from django.contrib.auth.models import User, Group, Permission
from aasemble.django.apps.buildsvc.models import Series, Repository
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase, override_settings

from aasemble.django.exceptions import CommandFailed
from aasemble.django.utils import run_cmd

stdout_stderr_script = '''#!/bin/sh

echo stdout
echo stderr >&2
'''


@override_settings(BUILDSVC_REPODRIVER='aasemble.django.apps.buildsvc.models.FakeDriver')
class AasembleTestCase(TestCase):
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


class UtilsTestCase(AasembleTestCase):
    def test_run_cmd_dead_simple(self):
        # Should simply return successfully
        stdout = run_cmd(['true'])
        self.assertEquals(stdout, b'')

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
            with os.fdopen(fd, 'w') as fp:
                rv = run_cmd(['echo', 'foo'], stdout=fp)

            self.assertEquals(rv, None)

            with open(tmpfile, 'r') as fp:
                self.assertEquals(fp.read(), 'foo\n')

        finally:
            os.unlink(tmpfile)

def create_default_group(name):
    #creating the group with all permissions
    permissions = Permission.objects.all()
    Group.objects.create(name=name)
    group =  Group.objects.get(name=name)
    #We need to add each permission one by one
    for permission in permissions:
        group.permissions.add(permission)
    return group
    
def create_default_repo(name, username):
    #Repo will be local repo.
    #We will give a static key_id value to avoid any confict.
    #geting the user. Make sure this already added before you pass it here
    user = User.objects.get(username=username)
    Repository.objects.create(user=user, name=name, key_id='12345') #Hope key id is unique.
    return Repository.objects.get(name=name)
    

def create_series(name, reponame):
    #geting the repo. Make sure this already added before you pass it here
    repo = Repository.objects.get(name=reponame)
    Series.objects.create(name=name, repository=repo)
    return Series.objects.get(name=name)


def delete_repo(name):
    repo = Repository.objects.get(name=name)
    repo.delete()

def delete_series(name):
    series = Series.objects.get(name=name)
    series.delete()

def delete_group(name):
    group = Group.objects.get(name=name)
    group.delete()

def delete_user(username):
    user = User.objects.get(username=username)
    user.delete()
