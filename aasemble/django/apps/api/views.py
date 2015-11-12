from allauth.account.adapter import DefaultAccountAdapter

from django.conf import settings

from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


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

        event_type = request.META['HTTP_X_GITHUB_EVENT']

        if event_type != 'push':
            return Response({'thanks': 'but no thanks'})

        github_push_event.delay(request.data['repository']['url'])

        return Response({'ok': 'thanks'})
