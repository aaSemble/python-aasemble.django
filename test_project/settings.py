"""
Test settings for Overcast project.

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
    'social.apps.django_app.default',
    'overcast.django.apps.main',
    'overcast.django.apps.buildsvc',
    'overcast.django.apps.mirrorsvc',
    'kombu.transport.django',
    'djcelery',
    'bootstrap3',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
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
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = (
    'social.backends.github.GithubOAuth2',
    'django.contrib.auth.backends.ModelBackend',
    'overcast.django.apps.buildsvc.auth.BuildSvcAuthzBackend',
)

WSGI_APPLICATION = 'test_project.wsgi.application'


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

SOCIAL_AUTH_GITHUB_KEY = None
SOCIAL_AUTH_GITHUB_SECRET = None
SOCIAL_AUTH_GITHUB_SCOPE = ['read:org']

BUILDSVC_REPOS_BASE_DIR = os.path.join(BASE_DIR, 'data', 'repos')
BUILDSVC_REPOS_BASE_PUBLIC_DIR = os.path.join(BASE_DIR, 'data', 'public_repos')
BUILDSVC_REPOS_BASE_URL = 'http://apt.overcastcloud.com'
BUILDSVC_DEFAULT_SERIES_NAME = 'overcast'

LOGIN_URL = '/login/github/'
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
    'poll-every-X-minutes': {
        'task': 'overcast.django.apps.buildsvc.tasks.poll_all',
        'schedule': timedelta(seconds=20),
    },
}

CELERY_TIMEZONE = TIME_ZONE
