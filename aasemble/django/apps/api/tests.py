import os.path

import mock

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


def authenticate(client, username=None, token=None):
    if token is None:
        token = Token.objects.get(user__username=username).key
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)


class APIv1Tests(APITestCase):
    fixtures = ['complete.json']


class APIv1RepositoryTests(APIv1Tests):
    list_url = '/api/v1/repositories/'

    def test_fetch_sources(self):
        # Use user brandon to make sure it works with users who are members
        # of multiple groups
        authenticate(self.client, 'brandon')
        response = self.client.get(self.list_url)

        for repo in response.data['results']:
            resp = self.client.get(repo['sources'])
            self.assertEquals(resp.status_code, 200)

    def test_fetch_external_dependencies(self):
        # Use brandon to make sure it works with users who are members
        # of multiple groups
        authenticate(self.client, 'brandon')
        response = self.client.get(self.list_url)

        for repo in response.data['results']:
            resp = self.client.get(repo['external_dependencies'])
            self.assertEquals(resp.status_code, 200)

    def test_create_repository_empty_fails_400(self):
        data = {}
        authenticate(self.client, 'eric')

        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'name': ['This field is required.']})

    def test_create_repository_no_auth_fails_401(self):
        data = {}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 401)

    def test_create_repository_incorrect_auth_fails_401(self):
        data = {}
        authenticate(self.client, token='invalidtoken')

        response = self.client.post(self.list_url, data, format='json')

        self.assertEquals(response.status_code, 401)

    def test_create_repository(self):
        data = {'name': 'testrepo'}
        authenticate(self.client, 'eric')

        response = self.client.post(self.list_url, data, format='json')

        self.assertEquals(response.status_code, 201)
        self.assertTrue(response.data['self'].startswith('http://testserver' + self.list_url), response.data['self'])
        expected_result = {'external_dependencies': response.data['self'] + 'external_dependencies/',
                           'name': 'testrepo',
                           'binary_source_list': 'deb http://127.0.0.1:8000/apt/eric/testrepo aasemble main',
                           'source_source_list': 'deb-src http://127.0.0.1:8000/apt/eric/testrepo aasemble main',
                           'self': response.data['self'],
                           'sources': response.data['self'] + 'sources/',
                           'user': 'eric',
                           'key_id': u''}

        self.assertEquals(response.data, expected_result)
        response = self.client.get(response.data['self'])
        self.assertEquals(response.data, expected_result)
        return response.data

    def test_create_duplicate_repository(self):
        data = {'name': 'testrepo'}
        authenticate(self.client, 'eric')
        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 201)
        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 409)

    def test_delete_repository(self):
        repo = self.test_create_repository()

        response = self.client.delete(repo['self'])

        self.assertEquals(response.status_code, 204)

        response = self.client.get(repo['self'])
        self.assertEquals(response.status_code, 404)

    def test_patch_repository(self):
        repo = self.test_create_repository()
        data = {'name': 'testrepo2'}

        response = self.client.patch(repo['self'], data, format='json')

        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['self'], repo['self'], '"self" attribute changed')

        expected_result = {'external_dependencies': response.data['self'] + 'external_dependencies/',
                           'name': 'testrepo2',
                           'binary_source_list': 'deb http://127.0.0.1:8000/apt/eric/testrepo2 aasemble main',
                           'source_source_list': 'deb-src http://127.0.0.1:8000/apt/eric/testrepo2 aasemble main',
                           'self': response.data['self'],
                           'sources': response.data['self'] + 'sources/',
                           'user': 'eric',
                           'key_id': u''}

        self.assertEquals(response.data, expected_result)

        response = self.client.get(response.data['self'])
        self.assertEquals(response.data, expected_result, 'Changes were not persisted')

    def test_patch_repository_read_only_field(self):
        repo = self.test_create_repository()
        data = {'user': 'testuser2'}

        self.client.patch(repo['self'], data, format='json')

    def test_delete_deleted_repository(self):
        repo = self.test_create_repository()

        response = self.client.delete(repo['self'])

        self.assertEquals(response.status_code, 204)

        response = self.client.delete(repo['self'])

        self.assertEquals(response.status_code, 404)

    def test_delete_repository_invalid_token(self):
        repo = self.test_create_repository()
        authenticate(self.client, token='invalidtoken')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 401)

    def test_delete_repository_other_user(self):
        repo = self.test_create_repository()
        authenticate(self.client, 'aaron')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 404)

    def test_delete_repository_super_user(self):
        repo = self.test_create_repository()
        authenticate(self.client, 'george')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 204)

    def test_patch_repository_other_user(self):
        repo = self.test_create_repository()
        data = {'name': 'testrepo2'}
        authenticate(self.client, 'aaron')
        response = self.client.patch(repo['self'], data, format='json')
        self.assertEquals(response.status_code, 404)

    def test_patch_repository_super_user(self):
        repo = self.test_create_repository()
        data = {'name': 'testrepo2'}
        authenticate(self.client, 'george')
        response = self.client.patch(repo['self'], data, format='json')
        self.assertEquals(response.status_code, 200)

    def test_delete_repository_deactivated_super_user(self):
        repo = self.test_create_repository()
        authenticate(self.client, 'harold')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 401)

    def test_delete_repository_deactivated_other_user(self):
        repo = self.test_create_repository()
        authenticate(self.client, 'frank')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 401)


class APIv2RepositoryTests(APIv1RepositoryTests):
    list_url = '/api/v2/repositories/'


class APIv1BuildTests(APIv1Tests):
    list_url = '/api/v1/builds/'

    def test_fetch_builds(self):
        # Use alterego2 to make sure it works with users who are members
        # of multiple groups
        authenticate(self.client, 'eric')
        response = self.client.get(self.list_url)
        self.assertEquals(response.status_code, 200)


class APIv2BuildTests(APIv1BuildTests):
    list_url = '/api/v2/builds/'


class APIv1SourceTests(APIv1Tests):
    list_url = '/api/v1/sources/'

    def test_create_source_empty_fails_400(self):
        data = {}
        authenticate(self.client, 'eric')

        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'git_repository': ['This field is required.'],
                                          'git_branch': ['This field is required.'],
                                          'repository': ['This field is required.']})

    def test_create_invalied_url_fails_400(self):
        data = {'git_repository': 'not a valid url'}
        authenticate(self.client, 'eric')

        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'git_repository': ['Enter a valid URL.'],
                                          'git_branch': ['This field is required.'],
                                          'repository': ['This field is required.']})

    def test_create_source_no_auth_fails_401(self):
        data = {}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 401)

    def test_create_source_incorrect_auth_fails_401(self):
        data = {}
        authenticate(self.client, token='invalidtoken')

        response = self.client.post(self.list_url, data, format='json')

        self.assertEquals(response.status_code, 401)

    def test_create_source(self):
        authenticate(self.client, 'eric')

        response = self.client.get(self.list_url.replace('sources', 'repositories'))

        data = {'git_repository': 'https://github.com/sorenh/buildsvctest',
                'git_branch': 'master',
                'repository': response.data['results'][0]['self']}

        response = self.client.post(self.list_url, data, format='json')

        self.assertEquals(response.status_code, 201)
        self.assertTrue(response.data['self'].startswith('http://testserver' + self.list_url), response.data['self'])
        data['self'] = response.data['self']
        data['builds'] = data['self'] + 'builds/'
        self.assertEquals(response.data, data)

        response = self.client.get(data['self'])
        self.assertEquals(response.data, data)
        return response.data

    def test_delete_source(self):
        source = self.test_create_source()

        response = self.client.delete(source['self'])

        self.assertEquals(response.status_code, 204)

        response = self.client.get(source['self'])
        self.assertEquals(response.status_code, 404)

    def test_delete_source_other_user(self):
        source = self.test_create_source()
        authenticate(self.client, 'aaron')
        response = self.client.delete(source['self'])
        self.assertEquals(response.status_code, 404)

    def test_delete_source_super_user(self):
        source = self.test_create_source()
        authenticate(self.client, 'george')
        response = self.client.delete(source['self'])
        self.assertEquals(response.status_code, 204)


class APIv2SourceTests(APIv1SourceTests):
    list_url = '/api/v2/sources/'


class APIv1AuthTests(APIv1Tests):
    self_url = '/api/v1/auth/user/'

    def test_get_user_details(self):
        authenticate(self.client, 'eric')

        response = self.client.get(self.self_url, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data,
                          {'username': u'eric',
                           'company': u'No Company',
                           'email': u'eric@example.com',
                           'avatar': u'https://avatars.githubusercontent.com/u/1234565?v=3',
                           'real_name': u'Eric Ericson'})


class APIv2AuthTests(APIv1AuthTests):
    self_url = '/api/v2/auth/user/'


class APIv1MirrorTests(APIv1Tests):
    list_url = '/api/v1/mirrors/'

    def test_create_mirror_empty_fails_400(self):
        data = {}
        authenticate(self.client, 'eric')

        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'url': ['This field is required.'],
                                          'series': ['This field is required.'],
                                          'components': ['This field is required.']})

    def test_create_mirror_invalid_url_fails(self):
        data = {'url': 'not-a-url',
                'series': ['trusty'],
                'components': ['main']}
        authenticate(self.client, 'eric')

        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'url': ['Enter a valid URL.']})

    def test_create_mirror(self):
        data = {'url': 'http://example.com/',
                'series': ['trusty'],
                'components': ['main']}
        authenticate(self.client, 'eric')

        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 201)
        self.assertTrue(response.data['self'].startswith('http://testserver' + self.list_url), response.data['self'])
        data['self'] = response.data['self']
        data['refresh_in_progress'] = False
        data['public'] = False
        self.assertEquals(data, response.data)
        return response.data

    @mock.patch('aasemble.django.apps.mirrorsvc.tasks.refresh_mirror')
    def test_refresh_mirror(self, refresh_mirror):
        mirror = self.test_create_mirror()
        self.client.post(mirror['self'] + 'refresh/')
        self.assertTrue(refresh_mirror.delay.call_args_list)


class APIv2MirrorTests(APIv1MirrorTests):
    list_url = '/api/v2/mirrors/'


class GithubHookViewTestCase(APIv1Tests):
    @mock.patch('aasemble.django.apps.api.tasks.github_push_event')
    def test_hook(self, github_push_event):
        with open(os.path.join(os.path.dirname(__file__), 'example-hook.json'), 'r') as fp:
            res = self.client.post('/api/events/github/',
                                   data=fp.read(),
                                   content_type='application/json',
                                   HTTP_X_GITHUB_EVENT='push')
        self.assertEquals(res.data, {'ok': 'thanks'})
        github_push_event.delay.assert_called_with("https://github.com/baxterthehacker/public-repo")

    @mock.patch('aasemble.django.apps.buildsvc.tasks.poll_one')
    def test_github_push_event(self, poll_one):
        from .tasks import github_push_event
        github_push_event("https://github.com/eric/project0")
        poll_one.delay.assert_called_with(1)
