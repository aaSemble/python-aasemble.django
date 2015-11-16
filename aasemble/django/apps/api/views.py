import logging

from allauth.account.adapter import DefaultAccountAdapter

from django.conf import settings

from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

LOG = logging.getLogger(__name__)


class MyUserAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        if not user.username:
            user.username = user.email

    def get_email_confirmation_url(self, request, emailconfirmation):
        return settings.EMAIL_CONFIRMATION_URL % (emailconfirmation.key,)


class GithubHookView(CreateAPIView):
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        from .tasks import github_push_event

        try:
            event_type = request.META['HTTP_X_GITHUB_EVENT']
            url = request.data['repository']['url']
            LOG.info('Got %s event for %s from Github' % (event_type, url))

            if event_type != 'push':
                return Response({'thanks': 'cool story bro'})

            github_push_event.delay(url)

            return Response({'ok': 'thanks'})
        except KeyError:
            return Response({"it's not me": "it's you"})
