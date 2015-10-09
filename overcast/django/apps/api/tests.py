from django.core.urlresolvers import reverse
from rest_framework.test import APIClient, APIRequestFactory, APITestCase
from rest_framework.authtoken.models import Token

def authenticate(client, username=None, token=None):
    if token is None:
        token = Token.objects.get(user__username=username).key
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)

class APIv1Tests(APITestCase):
    fixtures = ['data2.json']

    def test_create_repository_empty_fails_400(self):
        url = '/api/v1/repositories/'
        data = {}
        authenticate(self.client, 'testuser')

        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'name': ['This field is required.']})


    def test_create_repository_no_auth_fails_401(self):
        url = '/api/v1/repositories/'
        data = {}
        response = self.client.post(url, data, format='json')
        self.assertEquals(response.status_code, 401)


    def test_create_repository_incorrect_auth_fails_401(self):
        url = '/api/v1/repositories/'
        data = {}
        authenticate(self.client, token='invalidtoken')

        response = self.client.post(url, data, format='json')

        self.assertEquals(response.status_code, 401)

    def test_create_repository(self):
        url = '/api/v1/repositories/'
        data = {'name': 'testrepo'}
        authenticate(self.client, 'testuser')

        response = self.client.post(url, data, format='json')

        self.assertEquals(response.status_code, 201)
        self.assertTrue(response.data['self'].startswith('http://testserver/api/v1/repositories/'))
        expected_result = {'external_dependencies': response.data['self'] + 'external_dependencies/',
                           'name': 'testrepo',
                           'binary_source_list': 'deb http://127.0.0.1:8000/apt/testuser/testrepo overcast main',
                           'source_source_list': 'deb-src http://127.0.0.1:8000/apt/testuser/testrepo overcast main',
                           'self': response.data['self'],
                           'sources': response.data['self'] + 'sources/',
                           'user': 'testuser',
                           'key_id': u''}

        self.assertEquals(response.data, expected_result)
        response = self.client.get(response.data['self'])
        self.assertEquals(response.data, expected_result)
