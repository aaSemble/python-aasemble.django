"""
Test settings for aaSemble

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'wow-this-is-so-random'
DEBUG = True
ALLOWED_HOSTS = []
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'aasemble.django.apps.main',
    'aasemble.django.apps.api',
    'aasemble.django.apps.buildsvc',
    'aasemble.django.apps.mirrorsvc',
    'bootstrap3',
    'djcelery',
    'rest_framework',
    'rest_framework.authtoken',
    'kombu.transport.django',
    'corsheaders',
    'rest_auth',
    'rest_auth.registration',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    'rest_framework_tracking',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'test_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.core.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'aasemble.django.apps.main.context_processors.internal_name_change',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    'allauth.account.auth_backends.AuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
    'aasemble.django.apps.buildsvc.auth.BuildSvcAuthzBackend',
)

WSGI_APPLICATION = 'test_project.wsgi.application'


if os.environ.get('TRAVIS', '') == 'true':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'aasemble',
            'USER': 'test',
            'PASSWORD': '',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = 'staticfiles'

BUILDSVC_REPOS_BASE_DIR = os.path.join(BASE_DIR, 'data', 'repos')
BUILDSVC_REPOS_BASE_PUBLIC_DIR = os.path.join(BASE_DIR, 'data', 'public_repos')
BUILDSVC_REPOS_BASE_URL = 'http://127.0.0.1:8000/apt'
BUILDSVC_DEFAULT_SERIES_NAME = 'aasemble'
BUILDSVC_DEBEMAIL = 'pkgbuild@aasemble.com'
BUILDSVC_DEBFULLNAME = 'aaSemble Package Builder'

MIRRORSVC_BASE_PATH = os.path.join(BASE_DIR, 'mirrors')
MIRRORSVC_BASE_URL = 'http://127.0.0.1:8000/mirrors'

LOGIN_URL = '/accounts/github/login/'
LOGIN_REDIRECT_URL = '/'

SITE_ID = 1

CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
BROKER_URL = 'django://'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'my_cache_table',
    }
}

CELERYBEAT_SCHEDULE = {
    'poll-very-frequently': {
        'task': 'aasemble.django.apps.buildsvc.tasks.poll_all',
        'schedule': timedelta(seconds=10),
    },
}

CELERY_TIMEZONE = TIME_ZONE
GITHUB_AUTH_CALLBACK = 'http://localhost:8000/'
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.DjangoObjectPermissions',),
    'PAGE_SIZE': 100,
    'URL_FIELD_NAME': 'self',
}

AASEMBLE_BUILDSVC_BUILDER_HTTP_PROXY = os.environ.get('http_proxy')

CORS_ORIGIN_WHITELIST = ()
CORS_ALLOW_CREDENTIALS = True

# Request access to user's org memberships
SOCIALACCOUNT_PROVIDERS = {'github': {'SCOPE': ['read:org', 'user:email']}}

# Don't send account verification e-mails
ACCOUNT_EMAIL_VERIFICATION = "none"

# Use https when generating links for e-mails
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http'

# Use e-mail address as the "username". Not a username.
# Not a username or e-mail address. Just an e-mail address.
ACCOUNT_AUTHENTICATION_METHOD = 'email'

# There has to be an e-mail address. ACCOUNT_AUTHENTICATION_METHOD='email' requires it.
ACCOUNT_EMAIL_REQUIRED = True

# Usernames suck. People forget them, the good ones are always taken, etc. E-mail.
ACCOUNT_USERNAME_REQUIRED = False

# Users can sign up via Github
SOCIALACCOUNT_AUTO_SIGNUP=True

# Must e-mail addresses be unique? Hells yeah!
ACCOUNT_UNIQUE_EMAIL=True


REST_SESSION_LOGIN = False

DEFAULT_FROM_EMAIL = 'noreply@aasemble.com'

REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'aasemble.django.apps.api.serializers.UserDetailsSerializer'
}

# Import local development server settings. settings_local is not present in git, not relevant for production deployment

try:
    from settings_local import *
except ImportError as e:
    pass
