Overcast Cloud Web

To enable Github authentication (without which you won't be able to really do anything useful), go to [https://github.com/settings/applications/new](GitHub Developers) and register an application. Set the auth callback url to something like `http://localhost:8000/accounts/github/login/callback/`.

Go to the django admin interface. Update the example Site to point to `localhost:8000`. Then go to the `Social Applications` and create a new one using the keys from github and apply it to the localhost site.

That should do it. Have fun!
