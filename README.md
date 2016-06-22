[![Travis-CI Status](https://travis-ci.org/aaSemble/python-aasemble.django.svg)](https://travis-ci.org/aaSemble/python-aasemble.django)
[![codecov.io](https://codecov.io/github/aaSemble/python-aasemble.django/coverage.svg?branch=master)](https://codecov.io/github/aaSemble/python-aasemble.django?branch=master)

# aaSemble web services

## Introduction

## Setup

Install dependencies:

```
apt-get install libmysqlclient-dev python-dev libffi-dev

apt-get install docker.io
docker pull ubuntu
```

Setup a working environment:

```
git clone https://github.com/aaSemble/python-aasemble.django.git
cd python-aasemble.django/
virtualenv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

To run the web service:

```
python manage.py runserver [<ip_to_listen>:<port>]
```

To enable Github authentication (without which you won't be able to really do anything useful), go to [https://github.com/settings/applications/new](GitHub Developers) and register an application. Set the auth callback url to something like `http://localhost:8000/accounts/github/login/callback/`.

Create a superuser (`python manage.py createsuperuser`) and login to the django admin interface at `localhost:8000/admin`. Update the example.com Site to point to `localhost:8000`. Then go to the `Social Applications` and create a new one using the keys from github and apply it to the localhost site.

## Testing

To execute tests:

```
python manage.py test --verbosity 2
```

To execute a specific test suite:

```
python manage.py test aasemble.django.apps.api.tests.APIv1RepositoryTests
```

We use codecov to report test coverage. Install their [browser plugin](https://github.com/codecov/browser-extension) to see the coverage results overlayed over the code on Github. It's pretty awesome.

That should do it. Have fun!
