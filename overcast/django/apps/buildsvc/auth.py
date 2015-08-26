class BuildSvcAuthzBackend(object):
    def has_perm(self, user, perm, obj=None):
        if not user.is_active():
            return False

        if obj is None:
            # Leave this case to the other backend(s)
            return False

        if hasattr(obj, 'user_can_modify'):
            return obj.user_can_modify(user)
