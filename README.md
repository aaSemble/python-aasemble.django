[![Travis-CI Status](https://travis-ci.org/aaSemble/python-aasemble.django.svg)](https://travis-ci.org/aaSemble/python-aasemble.django)
[![codecov.io](https://codecov.io/github/aaSemble/python-aasemble.django/coverage.svg?branch=master)](https://codecov.io/github/aaSemble/python-aasemble.django?branch=master)

# aaSemble web services

## Introduction

## Setup

Install dependencies:

```
apt-get install libmysqlclient-dev python-dev libffi-dev reprepro

# Get docker from docker.io since the one from Ubuntu repos is older than version 1.22
wget -qO- https://get.docker.com/ | sh
docker pull ubuntu

# ensure that the user which runs the webservice (in particular *build api*)
# is part of docker group
usermod -aG docker vagrant
```

Setup a working environment:

```
git clone https://github.com/aaSemble/python-aasemble.django.git
cd python-aasemble.django/
virtualenv .venv
. .venv/bin/activate
pip install -U pip wheel
pip install -U -r requirements.txt
python manage.py migrate
python setup.py install
```

Get Celery running in the background

```
apt-get install redis-server

redis-cli ping

celery worker --detach
```

or

```
$ python manage.py celeryd_detach -B --logfile celery_logs.log
```

Update environment variables to match your setup

```
vi test_project/settings.py

BUILDSVC_REPOS_BASE_URL = 'http://x.x.x.x:8000/apt'
MIRRORSVC_BASE_URL = 'http://x.x.x.x:8000/mirrors'
GITHUB_AUTH_CALLBACK = 'http://x.x.x.x:8000/accounts/github/login/callback/'
AASEMBLE_BUILDSVC_EXECUTOR = 'Local'
```


In the case you want to use the superuser for testing, you will need to create the resouces manually

```
(.venv)vagrant@aasemble-build:~/python-aasemble.django$ python manage.py shell
>>>
from aasemble.django.apps.buildsvc import models as build_models
from django.contrib.auth import models as auth_models
u = auth_models.User.objects.get(username='vagrant')
r = build_models.Repository(user=u, name=u.username)
r.save()
s = build_models.Series(repository=r, name='aasemble')
s.save()
```

Now, goto http://x.x.x.x:8000/admin/sites/site/1/change/
and change example.com to x.x.x.x:8000

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
