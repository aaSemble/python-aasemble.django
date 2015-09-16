from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_auth.registration.views import SocialLoginView

class GithubLogin(SocialLoginView):
    callback_url = 'http://dev.overcastcloud.com/static/index.html'
    adapter_class = GitHubOAuth2Adapter
    client_class =  OAuth2Client
