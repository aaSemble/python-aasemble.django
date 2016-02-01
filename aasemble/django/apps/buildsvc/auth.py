from django.contrib.auth.models import User

class BuildSvcAuthzBackend(object):
    known_actions = ('add', 'delete', 'change')

    known_app_models = (('buildsvc', 'repository'),
                        ('buildsvc', 'packagesource'),
                        ('buildsvc', 'externaldependency'),
                        ('mirrorsvc', 'mirror'),
                        ('mirrorsvc', 'mirrorset'),
                        ('mirrorsvc', 'snapshot'))

    def get_user(self, user_id):
        """The Django documentation says this method is required[1],
        but it's not clear when it'll ever get called. It's very
        straightforward, though, so here it is."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def authenticate(self, *args, **kwargs):
        """Seeing as this backend is strictly for authorization, not
        authentication, just return None. Django will keep trying
        backends until one agrees to authenticate the user"""
        return None

    def get_app_perm_action_model(self, perm):
        app, perm = perm.split('.')
        action, model = perm.split('_')
        return app, perm, action, model

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False

        app, perm, action, model = self.get_app_perm_action_model(perm)

        if action not in self.known_actions:
            return False

        if (app, model) in self.known_app_models:
            # Django will first ask if the user is authorized to perform
            # the given action on the given model *at all*, and subsequently
            # check for access to a specific instance of the given model.
            # Hence, we have to return True here and just hope that it's
            # followed up by an object-level check.
            if obj is None:
                return True

            if hasattr(obj, 'user_can_modify'):
                return obj.user_can_modify(user_obj)
            else:
               return False
