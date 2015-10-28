[![Travis-CI Status](https://travis-ci.org/aaSemble/python-aasemble.django.svg)](https://travis-ci.org/aaSemble/python-aasemble.django)
[![Circle CI Status](https://circleci.com/gh/aaSemble/python-aasemble.django.svg?style=svg)](https://circleci.com/gh/aaSemble/python-aasemble.django)

# aaSemble web services


To enable Github authentication (without which you won't be able to really do anything useful), go to [https://github.com/settings/applications/new](GitHub Developers) and register an application. Set the auth callback url to something like `http://localhost:8000/accounts/github/login/callback/`.

Create a superuser (`python manage.py createsuperuser`) and login to the django admin interface at `localhost:8000/admin`. Update the example.com Site to point to `localhost:8000`. Then go to the `Social Applications` and create a new one using the keys from github and apply it to the localhost site.

That should do it. Have fun!
