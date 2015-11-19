from allauth.socialaccount.models import SocialToken

from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site

from rest_framework import serializers


class UserDetailsSerializer(serializers.ModelSerializer):
    real_name = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    github_token = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        return self.get_github_field(obj, 'avatar_url')

    def get_company(self, obj):
        return self.get_github_field(obj, 'company')

    def get_real_name(self, obj):
        return self.get_github_field(obj, 'name')

    def get_github_field(self, obj, field_name, default_value=None):
        gh_accounts = obj.socialaccount_set.filter(provider='github')
        if gh_accounts:
            return gh_accounts[0].extra_data[field_name]

        return default_value

    def get_github_token(self, obj):
        request = self.context['request']
        site = get_current_site(request)
        gh_accounts = obj.socialaccount_set.filter(provider='github')
        token = SocialToken.objects.filter(account__in=gh_accounts,
                                           app__in=site.socialapp_set.all())[0]
        return token.token

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'real_name', 'company', 'avatar', 'github_token')
        read_only_fields = ('email', 'real_name', 'company', 'avatar', 'github_token')
