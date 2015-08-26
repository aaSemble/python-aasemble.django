from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from . import utils, models

@receiver(post_save, sender=User)
def user_save_handler(sender, **kwargs):
    """This method gets called each time the user logs in!"""
    user = kwargs['instance']
    if user.social_auth.exists():
        utils.sync_sources_from_github(user)
        if not user.repository_set.exists():
            repository = models.Repository(user=user, name=user.username)
            repository.save()
        for repo in user.repository_set.all():
            if not repo.series_set.exists():
                series = models.Series(repository=repo, name=settings.BUILDSVC_DEFAULT_SERIES_NAME)
                series.save()
