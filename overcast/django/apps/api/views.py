from django.conf import settings
from django.contrib.sites import models as site_models

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_auth.registration.views import SocialLoginView

class GithubLogin(SocialLoginView):
    callback_url = settings.GITHUB_AUTH_CALLBACK
    adapter_class = GitHubOAuth2Adapter
    client_class =  OAuth2Client

class MyUserAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        if not user.username:
            user.username = user.email

    def get_email_confirmation_url(self, request, emailconfirmation):
        return settings.EMAIL_CONFIRMATION_URL % (emailconfirmation.key,)
