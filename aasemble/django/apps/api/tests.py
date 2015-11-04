from django.core.urlresolvers import reverse
from rest_framework.test import APIClient, APIRequestFactory, APITestCase
from rest_framework.authtoken.models import Token

def authenticate(client, username=None, token=None):
    if token is None:
        token = Token.objects.get(user__username=username).key
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)


class APIv1Tests(APITestCase):
    fixtures = ['data.json', 'data2.json']


class APIv1RepositoryTests(APIv1Tests):
    list_url = '/api/v1/repositories/'

    def test_fetch_sources(self):
        # Use alterego2 to make sure it works with users who are members
        # of multiple groups
        authenticate(self.client, 'alterego2')
        response = self.client.get(self.list_url)

        for repo in response.data['results']:
            resp = self.client.get(repo['sources'])
            self.assertEquals(resp.status_code, 200)

    def test_fetch_external_dependencies(self):
        # Use alterego2 to make sure it works with users who are members
        # of multiple groups
        authenticate(self.client, 'alterego2')
        response = self.client.get(self.list_url)

        for repo in response.data['results']:
            resp = self.client.get(repo['external_dependencies'])
            self.assertEquals(resp.status_code, 200)

    def test_create_repository_empty_fails_400(self):
        data = {}
        authenticate(self.client, 'testuser')

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
        authenticate(self.client, 'testuser')

        response = self.client.post(self.list_url, data, format='json')

        self.assertEquals(response.status_code, 201)
        self.assertTrue(response.data['self'].startswith('http://testserver' + self.list_url), response.data['self'])
        expected_result = {'external_dependencies': response.data['self'] + 'external_dependencies/',
                           'name': 'testrepo',
                           'binary_source_list': 'deb http://127.0.0.1:8000/apt/testuser/testrepo aasemble main',
                           'source_source_list': 'deb-src http://127.0.0.1:8000/apt/testuser/testrepo aasemble main',
                           'self': response.data['self'],
                           'sources': response.data['self'] + 'sources/',
                           'user': 'testuser',
                           'key_id': u''}

        self.assertEquals(response.data, expected_result)
        response = self.client.get(response.data['self'])
        self.assertEquals(response.data, expected_result)
        return response.data


    def test_create_duplicate_repository(self):
        data = {'name': 'testrepo'}
        authenticate(self.client, 'testuser')
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
                           'binary_source_list': 'deb http://127.0.0.1:8000/apt/testuser/testrepo2 aasemble main',
                           'source_source_list': 'deb-src http://127.0.0.1:8000/apt/testuser/testrepo2 aasemble main',
                           'self': response.data['self'],
                           'sources': response.data['self'] + 'sources/',
                           'user': 'testuser',
                           'key_id': u''}

        self.assertEquals(response.data, expected_result)

        response = self.client.get(response.data['self'])
        self.assertEquals(response.data, expected_result, 'Changes were not persisted')

    def test_patch_repository_read_only_field(self):
        repo = self.test_create_repository()
        data = {'user': 'testuser2'}

        response = self.client.patch(repo['self'], data, format='json')


class APIv2RepositoryTests(APIv1RepositoryTests):
    list_url = '/api/v2/repositories/'


class APIv1BuildTests(APIv1Tests):
    fixtures = ['data.json', 'data2.json', 'repository.json']

    list_url = '/api/v1/builds/'

    def test_fetch_builds(self):
        # Use alterego2 to make sure it works with users who are members
        # of multiple groups
        authenticate(self.client, 'alterego2')
        response = self.client.get(self.list_url)
        self.assertEquals(response.status_code, 200)


class APIv2BuildTests(APIv1BuildTests):
    list_url = '/api/v2/builds/'


class APIv1SourceTests(APIv1Tests):
    fixtures = ['data.json', 'data2.json', 'repository.json']

    list_url = '/api/v1/sources/'

    def test_create_source_empty_fails_400(self):
        data = {}
        authenticate(self.client, 'testuser')

        response = self.client.post(self.list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'git_repository': ['This field is required.'],
                                          'git_branch': ['This field is required.'],
                                          'repository': ['This field is required.']})


    def test_create_invalied_url_fails_400(self):
        data = {'git_repository': 'not a valid url'}
        authenticate(self.client, 'testuser')

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
        authenticate(self.client, 'testuser')

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


class APIv2SourceTests(APIv1SourceTests):
    fixtures = ['data.json', 'data2.json', 'repository.json']

    list_url = '/api/v2/sources/'


class APIv1AuthTests(APIv1Tests):
    def test_get_user_details(self):
        authenticate(self.client, 'testuser')

        response = self.client.get('/api/v1/auth/user/', format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data,
                          {'username': u'testuser',
                           'company': u'aaSemble',
                           'email': u'test1@example.com',
                           'avatar': u'https://avatars.githubusercontent.com/u/160090?v=3',
                           'real_name': u'Soren Hansen'})
