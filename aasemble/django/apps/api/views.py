from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class GithubHookView(CreateAPIView):
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        from .tasks import github_push_event

        event_type = request.META['HTTP_X_GITHUB_EVENT']

        if event_type != 'push':
            return Response({'thanks': 'but no thanks'})

        github_push_event.delay(request.data['repository']['url'])

        return Response({'ok': 'thanks'})
