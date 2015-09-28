class BuildSvcAuthzBackend(object):
    def authenticate(self, *args, **kwargs):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False

        app, perm_ = perm.split('.')
        if app == 'buildsvc':
            action, model = perm_.split('_')
            if (model in ('packagesource', 'externaldependency') and
                action in ('add', 'delete', 'change')):
                # This is pretty nuts. If we don't return True here,
                # django-rest-framework aborts immediately. So, we say
                # "sure!" and hope it asks for permission for the specific
                # object.
                if obj is None:
                    return True

            if hasattr(obj, 'user_can_modify'):
                return obj.user_can_modify(user_obj)
