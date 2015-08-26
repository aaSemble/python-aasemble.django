Overcast Cloud Web

To enable Github authentication (without which you won't be able to really do anything useful), go to [https://github.com/settings/applications/new](GitHub Developers) and register an application. Set the auth callback url to something like http://127.0.0.1:8000/complete/github/. Take the client id and client secret and put them in `test\_project/settings.py`.
