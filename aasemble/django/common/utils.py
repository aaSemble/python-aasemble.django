from aasemble.django.common import models


def user_has_feature(user, feature_name):
    try:
        feature = models.Feature.objects.get(name=feature_name)
    except models.Feature.DoesNotExist:
        return False

    if feature.on_by_default:
        return True

    if user in feature.users.all():
        return True

    return False
