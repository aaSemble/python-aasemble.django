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

from aasemble.django.utils import recursive_render


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
