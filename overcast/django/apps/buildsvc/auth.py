class BuildSvcAuthzBackend(object):
    def authenticate(self, *args, **kwargs):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False

        if perm == 'buildsvc.delete_packagesource':
            # This is pretty nuts. If we don't return True here,
            # django-rest-framework aborts immediately.
            # It then asks us afterwards if deleting a specific
            # object is ok.
            if obj is None:
                return True

        if obj is None:
            if perm == 'buildsvc.add_packagesource':
                return True
            # Leave this case to the other backend(s)
            return False

        if hasattr(obj, 'user_can_modify'):
            return obj.user_can_modify(user_obj)
