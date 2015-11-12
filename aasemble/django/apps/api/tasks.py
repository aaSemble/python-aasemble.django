from celery import shared_task

from aasemble.django.apps.buildsvc import models as buildsvc_models
from aasemble.django.apps.buildsvc import tasks as buildsvc_tasks


@shared_task(ignore_result=True)
def github_push_event(url):
    for ps in buildsvc_models.PackageSource.objects.filter(git_url=url):
        buildsvc_tasks.poll_one.delay(ps.id)
