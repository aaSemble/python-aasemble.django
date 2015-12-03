import os.path

import mock

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from six.moves.urllib.parse import urlparse


def authenticate(client, username=None, token=None):
    if token is None:
        token = Token.objects.get(user__username=username).key
    client.credentials(HTTP_AUTHORIZATION='Token ' + token)


class APIv1Tests(APITestCase):
    fixtures = ['complete.json']
    base_url = '/api/v1/'
    source_should_be_embedded_in_build = False
    build_includes_duration = False

    def __init__(self, *args, **kwargs):
        super(APIv1Tests, self).__init__(*args, **kwargs)
        self.repository_list_url = self.base_url + 'repositories/'
        self.mirrorset_list_url = self.base_url + 'mirror_sets/'
        self.snapshot_list_url = self.base_url + 'snapshots/'
        self.mirror_list_url = self.base_url + 'mirrors/'
        self.self_url = self.base_url + 'auth/user/'
        self.source_list_url = self.base_url + 'sources/'
        self.build_list_url = self.base_url + 'builds/'

    ####################
    # Repository tests #
    ####################

    def test_fetch_external_dependencies(self):
        # Use brandon to make sure it works with users who are members
        # of multiple groups
        authenticate(self.client, 'brandon')
        response = self.client.get(self.repository_list_url)

        for repo in response.data['results']:
            resp = self.client.get(repo['external_dependencies'])
            self.assertEquals(resp.status_code, 200)

    def test_fetch_repository_invalid_user(self, user='frank'):
        authenticate(self.client, user)
        response = self.client.get(self.repository_list_url)
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_fetch_repository_invalid_super_user(self):
        self.test_fetch_repository_invalid_user(user='harold')

    def test_create_repository_empty_fails_400(self):
        data = {}
        authenticate(self.client, 'eric')
        response = self.client.post(self.repository_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'name': ['This field is required.']})

    def test_create_repository_no_auth_fails_401(self):
        data = {}
        response = self.client.post(self.repository_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Authentication credentials were not provided.'})

    def test_create_repository_incorrect_auth_fails_401(self):
        data = {}
        authenticate(self.client, token='invalidtoken')
        response = self.client.post(self.repository_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_create_repository(self, user='eric'):
        data = {'name': 'testrepo'}
        authenticate(self.client, user)
        response = self.client.post(self.repository_list_url, data, format='json')
        self.assertEquals(response.status_code, 201)
        self.assertTrue(response.data['self'].startswith('http://testserver' + self.repository_list_url), response.data['self'])
        expected_result = {'external_dependencies': response.data['self'] + 'external_dependencies/',
                           'name': 'testrepo',
                           'binary_source_list': 'deb http://127.0.0.1:8000/apt/%s/testrepo aasemble main' % (user,),
                           'source_source_list': 'deb-src http://127.0.0.1:8000/apt/%s/testrepo aasemble main' % (user,),
                           'self': response.data['self'],
                           'sources': response.data['self'] + 'sources/',
                           'user': user,
                           'key_id': u''}
        self.assertEquals(response.data, expected_result)
        response = self.client.get(response.data['self'])
        self.assertEquals(response.data, expected_result)
        return response.data

    def test_create_repository_deactivated_user(self, user='frank'):
        data = {'name': 'testrepo'}
        authenticate(self.client, user)
        response = self.client.post(self.repository_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_create_repository_deactivated_super_user(self):
        self.test_create_repository_deactivated_user(user='harold')

    def test_create_duplicate_repository_same_group_different_members(self):
        self.test_create_repository(user='brandon')
        self.test_create_repository(user='charles')

    def test_create_duplicate_repository(self):
        data = {'name': 'testrepo'}
        self.test_create_repository()
        response = self.client.post(self.repository_list_url, data, format='json')
        self.assertEquals(response.status_code, 409)
        self.assertEquals(response.data, {'detail': 'Duplicate resource'})

    def test_delete_repository(self):
        repo = self.test_create_repository()
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 204)
        response = self.client.get(repo['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_repository_same_group_different_member(self):
        repo = self.test_create_repository(user='brandon')
        authenticate(self.client, 'charles')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

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
        response = self.client.patch(repo['self'], data, format='json')
        self.assertNotEquals(response.data['user'], 'testuser2', '"user" read-only field changed')

    def test_delete_deleted_repository(self):
        repo = self.test_create_repository()
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 204)
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_repository_invalid_token(self):
        repo = self.test_create_repository()
        authenticate(self.client, token='invalidtoken')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_delete_repository_other_user(self):
        repo = self.test_create_repository()
        authenticate(self.client, 'aaron')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

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
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_patch_repository_super_user(self):
        repo = self.test_create_repository()
        data = {'name': 'testrepo2'}
        authenticate(self.client, 'george')
        response = self.client.patch(repo['self'], data, format='json')
        self.assertEquals(response.status_code, 200)

    def test_patch_repository_deactivated_super_user(self):
        repo = self.test_create_repository()
        data = {'name': 'testrepo2'}
        authenticate(self.client, 'harold')
        response = self.client.patch(repo['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_patch_repository_deactivated_other_user(self):
        repo = self.test_create_repository()
        data = {'name': 'testrepo2'}
        authenticate(self.client, 'frank')
        response = self.client.patch(repo['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_delete_repository_deactivated_super_user(self):
        repo = self.test_create_repository()
        authenticate(self.client, 'harold')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_delete_repository_deactivated_other_user(self):
        repo = self.test_create_repository()
        authenticate(self.client, 'frank')
        response = self.client.delete(repo['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_create_same_name_repository_different_user(self):
        self.test_create_repository(user='eric')
        self.test_create_repository(user='dennis')

    ###############
    # Build tests #
    ###############

    def test_fetch_builds(self):
        authenticate(self.client, 'eric')
        # 6 queries: Create transaction, Authenticate, 1 logging entry, count results, fetch results,
        # rollback transaction
        with self.assertNumQueries(6):
            response = self.client.get(self.build_list_url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['count'], 10)

    def test_source_is_linked_or_nested(self):
        authenticate(self.client, 'eric')
        response = self.client.get(self.build_list_url)
        if self.source_should_be_embedded_in_build:
            self.assertTrue(isinstance(response.data['results'][0]['source'], dict))
        else:
            urlparse(response.data['results'][0]['source'])

    def test_duration_included_only_in_v3_and_beyond(self):
        authenticate(self.client, 'eric')
        response = self.client.get(self.build_list_url)
        self.assertEquals(self.build_includes_duration, 'duration' in response.data['results'][0])
        self.assertEquals(self.build_includes_duration, 'build_finished' in response.data['results'][0])

    ################
    # Source tests #
    ################

    def test_fetch_sources(self):
        authenticate(self.client, 'eric')
        # 6 queries: Create transaction, Authenticate, 1 logging entry, count results, fetch results,
        # rollback transaction
        with self.assertNumQueries(6):
            response = self.client.get(self.source_list_url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['count'], 12)

    def test_fetch_sources_by_repository(self):
        authenticate(self.client, 'eric')
        response = self.client.get(self.repository_list_url)
        for res in response.data['results']:
            if res['name'] == 'eric2':
                # 6 queries: Create transaction, Authenticate, 1 logging entry, count results, fetch results,
                # rollback transaction
                with self.assertNumQueries(6):
                    response = self.client.get(res['sources'])
                self.assertEquals(response.status_code, 200)
                self.assertEquals(response.data['count'], 2)
                return
        self.assertFalse(True, 'did not find the right repo')

    def test_create_source_empty_fails_400(self):
        data = {}
        authenticate(self.client, 'eric')
        response = self.client.post(self.source_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'git_repository': ['This field is required.'],
                                          'git_branch': ['This field is required.'],
                                          'repository': ['This field is required.']})

    def test_create_invalied_url_fails_400(self):
        data = {'git_repository': 'not a valid url'}
        authenticate(self.client, 'eric')
        response = self.client.post(self.source_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'git_repository': ['Enter a valid URL.'],
                                          'git_branch': ['This field is required.'],
                                          'repository': ['This field is required.']})

    def test_create_source_no_auth_fails_401(self):
        data = {}
        response = self.client.post(self.source_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Authentication credentials were not provided.'})

    def test_create_source_incorrect_auth_fails_401(self):
        data = {}
        authenticate(self.client, token='invalidtoken')
        response = self.client.post(self.source_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_create_source(self, user='eric'):
        authenticate(self.client, user)
        response = self.client.get(self.repository_list_url)
        data = {'git_repository': 'https://github.com/sorenh/buildsvctest',
                'git_branch': 'master',
                'repository': response.data['results'][0]['self']}
        response = self.client.post(self.source_list_url, data, format='json')
        self.assertEquals(response.status_code, 201)
        self.assertTrue(response.data['self'].startswith('http://testserver' + self.source_list_url), response.data['self'])
        data['self'] = response.data['self']
        data['builds'] = data['self'] + 'builds/'
        self.assertEquals(response.data, data)
        response = self.client.get(data['self'])
        self.assertEquals(response.data, data)
        return response.data

    def test_create_source_deactivated_user(self, user='frank'):
        authenticate(self.client, user)
        data = {}
        response = self.client.post(self.source_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_create_source_deactivated_super_user(self):
        self.test_create_source_deactivated_user(user='harold')

    def test_create_source_with_other_user_repository(self):
        authenticate(self.client, 'eric')
        response = self.client.get(self.repository_list_url)
        data = {'git_repository': 'https://github.com/sorenh/buildsvctest',
                'git_branch': 'master',
                'repository': response.data['results'][0]['self']}
        authenticate(self.client, 'aaron')
        response = self.client.post(self.source_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'repository': ['Invalid hyperlink - Object does not exist.']})

    def test_create_source_with_same_group_member_repository(self):
        data = {'name': 'testrepo'}
        authenticate(self.client, 'brandon')
        response = self.client.post(self.repository_list_url, data, format='json')
        data = {'git_repository': 'https://github.com/sorenh/buildsvctest',
                'git_branch': 'master',
                'repository': response.data['self']}
        authenticate(self.client, 'charles')
        response = self.client.post(self.source_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'repository': ['Invalid hyperlink - Object does not exist.']})

    def test_patch_source(self, user='eric'):
        source = self.test_create_source()
        repo = self.client.get(self.repository_list_url)
        data = {'repository': repo.data['results'][1]['self']}
        response = self.client.patch(source['self'], data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['repository'], repo.data['results'][1]['self'])

    def test_patch_source_invalid_data(self):
        source = self.test_create_source()
        data = {'repository': 'invalid repo URL'}
        response = self.client.patch(source['self'], data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'repository': ['Invalid hyperlink - No URL match.']})

    def test_patch_source_invalid_token(self):
        source = self.test_create_source()
        authenticate(self.client, token='invalidtoken')
        data = {}
        response = self.client.patch(source['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_patch_source_other_user(self):
        source = self.test_create_source()
        authenticate(self.client, 'aaron')
        data = {}
        response = self.client.patch(source['self'], data, format='json')
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_patch_source_super_user(self):
        source = self.test_create_source()
        authenticate(self.client, 'george')
        repo = self.client.get(self.repository_list_url)
        data = {'repository': repo.data['results'][0]['self']}
        response = self.client.patch(source['self'], data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['repository'], repo.data['results'][0]['self'])

    def test_patch_source_other_deactivated_user(self, user='frank'):
        source = self.test_create_source()
        authenticate(self.client, user)
        data = {}
        response = self.client.patch(source['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_patch_source_super_deactivated_user(self):
        self.test_patch_source_other_deactivated_user(user='harold')

    def test_patch_source_same_group_other_user(self):
        source = self.test_create_source(user='brandon')
        authenticate(self.client, 'charles')
        data = {}
        response = self.client.patch(source['self'], data, format='json')
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_source(self):
        source = self.test_create_source()
        response = self.client.delete(source['self'])
        self.assertEquals(response.status_code, 204)
        response = self.client.get(source['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_source_other_member_same_group(self):
        source = self.test_create_source(user='brandon')
        authenticate(self.client, 'charles')
        response = self.client.delete(source['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_source_other_user(self):
        source = self.test_create_source()
        authenticate(self.client, 'aaron')
        response = self.client.delete(source['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_source_super_user(self):
        source = self.test_create_source()
        authenticate(self.client, 'george')
        response = self.client.delete(source['self'])
        self.assertEquals(response.status_code, 204)

    def test_delete_source_invalid_token(self):
        source = self.test_create_source()
        authenticate(self.client, token='invalidtoken')
        response = self.client.delete(source['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_delete_source_deactivated_super_user(self):
        source = self.test_create_source()
        authenticate(self.client, 'harold')
        response = self.client.delete(source['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_delete_source_deactivated_other_user(self):
        source = self.test_create_source()
        authenticate(self.client, 'frank')
        response = self.client.delete(source['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    ################
    # Mirror tests #
    ################

    def test_create_mirror_empty_fails_400(self):
        data = {}
        authenticate(self.client, 'eric')
        response = self.client.post(self.mirror_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'url': ['This field is required.'],
                                          'series': ['This field is required.'],
                                          'components': ['This field is required.']})

    def test_create_mirror_no_auth_fails_401(self):
        data = {}
        response = self.client.post(self.mirror_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Authentication credentials were not provided.'})

    def test_create_mirror_incorrect_auth_fails_401(self):
        data = {}
        authenticate(self.client, token='invalidtoken')
        response = self.client.post(self.mirror_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_create_mirror_invalid_url_fails(self):
        data = {'url': 'not-a-url',
                'series': ['trusty'],
                'components': ['main']}
        authenticate(self.client, 'eric')
        response = self.client.post(self.mirror_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'url': ['Enter a valid URL.']})

    def test_create_mirror(self, user='eric'):
        data = {'url': 'http://example.com/',
                'series': ['trusty'],
                'components': ['main']}
        authenticate(self.client, user)
        response = self.client.post(self.mirror_list_url, data, format='json')
        self.assertEquals(response.status_code, 201)
        self.assertTrue(response.data['self'].startswith('http://testserver' + self.mirror_list_url), response.data['self'])
        data['self'] = response.data['self']
        data['refresh_in_progress'] = False
        data['public'] = False
        self.assertEquals(data, response.data)
        return response.data

    def test_patch_mirror(self, user='eric'):
        mirror = self.test_create_mirror(user)
        data = {'public': True}
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['public'], True)
        return response.data

    def test_patch_mirror_no_data(self):
        mirror = self.test_create_mirror()
        data = {}
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 200)

    def test_patch_mirror_invalid_token(self):
        mirror = self.test_create_mirror()
        data = {}
        authenticate(self.client, token='invalidtoken')
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_patch_mirror_other_user(self):
        mirror = self.test_create_mirror()
        data = {'public': True}
        authenticate(self.client, 'aaron')
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_patch_mirror_super_user(self):
        mirror = self.test_create_mirror()
        data = {'public': True}
        authenticate(self.client, 'george')
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['public'], True)

    def test_patch_public_mirror_other_user(self):
        mirror = self.test_patch_mirror()
        data = {'public': False}
        authenticate(self.client, 'aaron')
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 403)
        self.assertEquals(response.data, {'detail': 'You do not have permission to perform this action.'})

    def test_patch_mirror_same_group_other_user(self):
        mirror = self.test_create_mirror(user='brandon')
        data = {'public': True}
        authenticate(self.client, 'charles')
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_patch_public_mirror_same_group_other_user(self):
        mirror = self.test_patch_mirror(user='brandon')
        data = {'public': False}
        authenticate(self.client, 'charles')
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 403)
        self.assertEquals(response.data, {'detail': 'You do not have permission to perform this action.'})

    def test_patch_public_mirror_deactivated_other_user(self):
        mirror = self.test_patch_mirror()
        data = {'public': False}
        authenticate(self.client, 'harold')
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_patch_public_mirror_deactivated_super_user(self):
        mirror = self.test_patch_mirror()
        data = {'public': False}
        authenticate(self.client, 'frank')
        response = self.client.patch(mirror['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_delete_mirror(self):
        mirror = self.test_create_mirror()
        response = self.client.delete(mirror['self'])
        self.assertEquals(response.status_code, 204)
        response = self.client.get(mirror['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_public_mirror_other_user(self):
        mirror = self.test_patch_mirror()
        authenticate(self.client, 'aaron')
        response = self.client.delete(mirror['self'])
        self.assertEquals(response.status_code, 403)
        self.assertEquals(response.data, {'detail': 'You do not have permission to perform this action.'})

    def test_delete_public_mirror_same_group_other_user(self):
        mirror = self.test_patch_mirror(user='brandon')
        authenticate(self.client, 'charles')
        response = self.client.delete(mirror['self'])
        self.assertEquals(response.status_code, 403)
        self.assertEquals(response.data, {'detail': 'You do not have permission to perform this action.'})

    def test_delete_mirror_other_user(self):
        mirror = self.test_create_mirror()
        authenticate(self.client, 'aaron')
        response = self.client.delete(mirror['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_mirror_super_user(self):
        mirror = self.test_create_mirror()
        authenticate(self.client, 'george')
        response = self.client.delete(mirror['self'])
        self.assertEquals(response.status_code, 204)

    def test_delete_mirror_same_group_other_user(self):
        mirror = self.test_create_mirror(user='brandon')
        authenticate(self.client, 'charles')
        response = self.client.delete(mirror['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_mirror_invalid_token(self):
        mirror = self.test_create_mirror()
        authenticate(self.client, token='invalidtoken')
        response = self.client.delete(mirror['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_delete_mirror_deactivated_other_user(self, user='frank'):
        mirror = self.test_create_mirror()
        authenticate(self.client, user)
        response = self.client.delete(mirror['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_delete_mirror_deactivated_super_user(self):
        self.test_create_mirror()
        self.test_delete_mirror_deactivated_other_user(user='harold')

    @mock.patch('aasemble.django.apps.mirrorsvc.tasks.refresh_mirror')
    def test_refresh_mirror(self, refresh_mirror):
        mirror = self.test_create_mirror()
        self.client.post(mirror['self'] + 'refresh/')
        self.assertTrue(refresh_mirror.delay.call_args_list)

    def test_get_correct_mirror_for_user(self):
        self.test_create_mirror()
        data = {'url': 'http://example2.com/',
                'series': ['trusty'],
                'components': ['main']}
        authenticate(self.client, 'aaron')
        self.client.post(self.mirror_list_url, data, format='json')
        response = self.client.get(self.mirror_list_url)
        self.assertEquals(len(response.data['results']), 1, 'did not return only 1 mirror')
        self.assertEquals(response.data['results'][0]['url'], 'http://example2.com/', 'url not the same as created')

    @mock.patch('aasemble.django.apps.mirrorsvc.tasks.refresh_mirror')
    def test_refresh_mirror_status(self, refresh_mirror):
        mirror = self.test_create_mirror()
        response = self.client.post(mirror['self'] + 'refresh/')
        self.assertEquals(response.data['status'], 'update scheduled')
        response = self.client.post(mirror['self'] + 'refresh/')
        self.assertEquals(response.data['status'], 'update already scheduled')

    ####################
    # Mirror set tests #
    ####################

    def test_create_mirrorset_empty_fails_400(self):
        # An issue with django-rest-framework will result in returning a status
        # code of 201 CREATED on production or Django's development server.
        # This is a known issue: https://github.com/tomchristie/django-rest-framework/issues/3647
        data = {}
        authenticate(self.client, 'eric')
        response = self.client.post(self.mirrorset_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'mirrors': ['This field is required.']})

    def test_create_mirrorset_no_auth_fails_401(self):
        data = {}
        response = self.client.post(self.mirrorset_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Authentication credentials were not provided.'})

    def test_create_mirrorset_incorrect_auth_fails_401(self):
        data = {}
        authenticate(self.client, token='invalidtoken')
        response = self.client.post(self.mirrorset_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_create_mirrorset_invalid_mirrors(self):
        authenticate(self.client, 'eric')
        data = {'mirrors': ['Invalid Mirrors URL']}
        response = self.client.post(self.mirrorset_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'mirrors': ['Invalid hyperlink - No URL match.']})

    def test_create_mirrorset(self, user='eric'):
        response = self.test_create_mirror(user)
        data = {'mirrors': [response['self']]}
        response = self.client.post(self.mirrorset_list_url, data, format='json')
        self.assertEquals(response.status_code, 201)
        return response.data

    def test_patch_mirrorset_invalid_mirror(self):
        mirrorset = self.test_create_mirrorset()
        data = {'mirrors': ['Invalid Mirrors URL']}
        response = self.client.patch(mirrorset['self'], data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'mirrors': ['Invalid hyperlink - No URL match.']})

    def test_patch_mirrorset(self, user='eric'):
        mirrorset = self.test_create_mirrorset()
        data = {'url': 'http://example1.com/',
                'series': ['trusty'],
                'components': ['main']}
        authenticate(self.client, user)
        mirror = self.client.post(self.mirror_list_url, data, format='json')
        self.assertEquals(mirror.status_code, 201)
        data = {'mirrors': [mirror.data['self']]}
        response = self.client.patch(mirrorset['self'], data, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data['mirrors'], [mirror.data['self']])

    def test_patch_mirrorset_invalid_token(self):
        mirrorset = self.test_create_mirrorset()
        data = {}
        authenticate(self.client, token='invalidtoken')
        response = self.client.patch(mirrorset['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_patch_mirrorset_other_user(self):
        mirrorset = self.test_create_mirrorset()
        data = {}
        authenticate(self.client, 'aaron')
        response = self.client.patch(mirrorset['self'], data, format='json')
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_patch_mirrorset_other_user_same_group(self):
        mirrorset = self.test_create_mirrorset(user='brandon')
        data = {}
        authenticate(self.client, 'charles')
        response = self.client.patch(mirrorset['self'], data, format='json')
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_patch_mirrorset_no_data(self):
        mirrorset = self.test_create_mirrorset()
        data = {}
        response = self.client.patch(mirrorset['self'], data, format='json')
        self.assertEquals(response.status_code, 200)

    def test_patch_mirrorset_super_user(self):
        self.test_create_mirrorset()
        self.test_patch_mirrorset(user='george')

    def test_patch_mirrorset_deactivated_user(self, user='frank'):
        mirrorset = self.test_create_mirrorset()
        data = {}
        authenticate(self.client, user)
        response = self.client.patch(mirrorset['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_patch_mirrorset_deactivated_super_user(self):
        self.test_patch_mirrorset_deactivated_user(user='harold')

    def test_delete_mirrorset(self):
        mirrorset = self.test_create_mirrorset()
        response = self.client.delete(mirrorset['self'])
        self.assertEquals(response.status_code, 204)

    def test_delete_mirrorset_invalid_token(self):
        mirrorset = self.test_create_mirrorset()
        authenticate(self.client, token='invalidtoken')
        response = self.client.delete(mirrorset['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_delete_mirrorset_super_user(self):
        mirrorset = self.test_create_mirrorset()
        authenticate(self.client, 'george')
        response = self.client.delete(mirrorset['self'])
        self.assertEquals(response.status_code, 204)

    def test_delete_mirrorset_other_user(self):
        mirrorset = self.test_create_mirrorset()
        authenticate(self.client, 'aaron')
        response = self.client.delete(mirrorset['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_mirrorset_other_user_same_group(self):
        mirrorset = self.test_create_mirrorset(user='brandon')
        authenticate(self.client, 'charles')
        response = self.client.delete(mirrorset['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_mirrorset_deactivated_super_user(self):
        mirrorset = self.test_create_mirrorset()
        authenticate(self.client, 'harold')
        response = self.client.delete(mirrorset['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_delete_mirrorset_deactivated_other_user(self):
        mirrorset = self.test_create_mirrorset()
        authenticate(self.client, 'frank')
        response = self.client.delete(mirrorset['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    ##################
    # Snapshot tests #
    ##################

    def test_create_snapshot_no_auth_fails_401(self):
        data = {}
        response = self.client.post(self.snapshot_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Authentication credentials were not provided.'})

    def test_create_snapshot_empty_fails_400(self):
        data = {}
        authenticate(self.client, 'eric')

        response = self.client.post(self.snapshot_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'mirrorset': ['This field is required.']})

    def test_create_snapshot_incorrect_auth_fails_401(self):
        data = {}
        authenticate(self.client, token='invalidtoken')
        response = self.client.post(self.snapshot_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_create_snapshot(self, user='eric'):
        response = self.test_create_mirrorset()
        data = {'mirrorset': response['self']}
        response = self.client.post(self.snapshot_list_url, data, format='json')
        self.assertEquals(response.status_code, 201)
        return response.data

    def test_create_snapshot_invalid_mirrorset(self):
        authenticate(self.client, 'eric')
        data = {'mirrorset': 'Invalid Mirrorset URL'}
        response = self.client.post(self.snapshot_list_url, data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'mirrorset': ['Invalid hyperlink - No URL match.']})

    def test_create_snapshot_deactivated_user(self, user='frank'):
        data = {}
        authenticate(self.client, user)
        response = self.client.post(self.snapshot_list_url, data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_create_snapshot_deactivated_super_user(self):
        self.test_create_snapshot_deactivated_user(user='harold')

    def test_patch_snapshot_not_allowed(self, user='eric'):
        snapshot = self.test_create_snapshot()
        # no new mirror set is created because test case intend is different
        authenticate(self.client, user)
        data = {'mirrorset': snapshot['mirrorset']}
        response = self.client.patch(snapshot['self'], data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'detail': 'Method "PATCH" not allowed.'})

    def test_patch_snapshot_super_user_not_allowed(self):
        self.test_patch_snapshot_not_allowed(user='george')

    def test_patch_snapshot_other_user(self):
        snapshot = self.test_create_snapshot()
        authenticate(self.client, 'aaron')
        data = {'mirrorset': snapshot['mirrorset']}
        response = self.client.patch(snapshot['self'], data, format='json')
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_patch_snapshot_same_group_other_user(self):
        snapshot = self.test_create_snapshot(user='brandon')
        authenticate(self.client, 'charles')
        data = {'mirrorset': snapshot['mirrorset']}
        response = self.client.patch(snapshot['self'], data, format='json')
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_patch_snapshot_deactive_user(self, user='frank'):
        snapshot = self.test_create_snapshot()
        authenticate(self.client, user)
        data = {}
        response = self.client.patch(snapshot['self'], data, format='json')
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_patch_snapshot_deactive_super_user(self):
        self.test_patch_snapshot_deactive_user(user='harold')

    def test_delete_snapshot_no_auth(self):
        snapshot = self.test_create_snapshot()
        authenticate(self.client, token=' ')
        response = self.client.delete(snapshot['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token header. No credentials provided.'})

    def test_delete_snapshot(self, user='eric'):
        snapshot = self.test_create_snapshot()
        authenticate(self.client, user)
        response = self.client.delete(snapshot['self'])
        self.assertEquals(response.status_code, 204)

    def test_delete_snapshot_invalid_token(self):
        snapshot = self.test_create_snapshot()
        authenticate(self.client, token='invalidtoken')
        response = self.client.delete(snapshot['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'Invalid token.'})

    def test_delete_snapshot_other_user(self):
        snapshot = self.test_create_snapshot()
        authenticate(self.client, 'aaron')
        response = self.client.delete(snapshot['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_snapshot_super_user(self):
        self.test_delete_snapshot(user='george')

    def test_delete_snapshot_other_user_same_group(self):
        snapshot = self.test_create_snapshot(user='brandon')
        authenticate(self.client, 'charles')
        response = self.client.delete(snapshot['self'])
        self.assertEquals(response.status_code, 404)
        self.assertEquals(response.data, {'detail': 'Not found.'})

    def test_delete_snapshot_deactivated_super_user(self, user='harold'):
        snapshot = self.test_create_snapshot()
        authenticate(self.client, user)
        response = self.client.delete(snapshot['self'])
        self.assertEquals(response.status_code, 401)
        self.assertEquals(response.data, {'detail': 'User inactive or deleted.'})

    def test_delete_snapshot_deactivated_other_user(self):
        self.test_delete_snapshot_deactivated_super_user(user='frank')

    ##############
    # Auth tests #
    ##############

    def test_get_user_details(self):
        authenticate(self.client, 'eric')

        response = self.client.get(self.self_url, format='json')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.data,
                          {'username': u'eric',
                           'company': u'No Company',
                           'email': u'eric@example.com',
                           'avatar': u'https://avatars.githubusercontent.com/u/1234565?v=3',
                           'real_name': u'Eric Ericson',
                           'github_token': '2348765218564329856923487569324878732645'})


class APIv2Tests(APIv1Tests):
    base_url = '/api/v2/'

    def test_builds_default_order(self):
        authenticate(self.client, 'eric')
        response = self.client.get(self.build_list_url)
        prev_build = None
        for build in response.data['results']:
            if prev_build:
                self.assertGreater(build['build_started'],
                                   prev_build['build_started'])
            prev_build = build

    def test_builds_specific_order(self):
        authenticate(self.client, 'eric')
        response = self.client.get(self.build_list_url + '?ordering=-build_started')
        prev_build = None
        for build in response.data['results']:
            if prev_build:
                self.assertLess(build['build_started'],
                                prev_build['build_started'])
            prev_build = build

    def test_create_snapshot_tag(self):
        data = {'mirrorset': 'http://testserver{0}60d0ba66-d343-404b-a6e6-5c141db11a54/'.format(self.mirrorset_list_url),
                'tags': ['firsttag', 'secondtag']}
        authenticate(self.client, 'eric')
        response = self.client.post(self.snapshot_list_url, data, format='json')
        self.assertEquals(response.status_code, 201)
        data['self'] = response.data['self']
        data['timestamp'] = response.data['timestamp']
        self.assertEquals(data, response.data)
        return response.data

    def test_update_snapshot_tag(self):
        data = {'tags': ['thirdtag']}
        authenticate(self.client, 'eric')
        response = self.client.patch(self.snapshot_list_url + '470688a8-7294-4c17-b020-1d67aebaf972/', data, format='json')
        self.assertEquals(response.status_code, 200)
        data['self'] = response.data['self']
        data['timestamp'] = response.data['timestamp']
        data['mirrorset'] = response.data['mirrorset']
        self.assertEquals(data, response.data)
        return response.data

    def test_update_snapshot_mirrorset_400(self):
        data = {'mirrorset': 'http://testserver%smirror_sets/60d0ba66-d343-404b-a6e6-5c141db11a54/' % (self.base_url,)}
        authenticate(self.client, 'eric')
        response = self.client.patch(self.snapshot_list_url + '470688a8-7294-4c17-b020-1d67aebaf972/', data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'detail': 'Method "PATCH" not allowed.'})

    def test_update_snapshot_timestamp_400(self):
        data = {'timestamp': '2015-11-13T11:53:09.496Z'}
        authenticate(self.client, 'eric')
        response = self.client.patch(self.snapshot_list_url + '470688a8-7294-4c17-b020-1d67aebaf972/', data, format='json')
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.data, {'detail': 'Method "PATCH" not allowed.'})

    def test_filter_snapshot_tag(self):
        data = {'tags': ['fourthtag', 'fifthtag']}
        authenticate(self.client, 'eric')
        response1 = self.client.patch(self.snapshot_list_url + '470688a8-7294-4c17-b020-1d67aebaf972/', data, format='json')
        self.assertEquals(response1.status_code, 200)
        response2 = self.client.get(self.base_url + 'snapshots/?tag=fourthtag')
        self.assertEquals(response1.data, response2.data["results"][0])
        return response2.data


class APIv3Tests(APIv2Tests):
    base_url = '/api/v3/'
    source_should_be_embedded_in_build = True
    build_includes_duration = True

    def test_build_duration(self):
        authenticate(self.client, 'eric')
        response = self.client.get(self.build_list_url)
        for result in response.data['results']:
            if result['version'] == '1.1+0':
                self.assertEquals(result['duration'], 81)
            else:
                self.assertEquals(result['duration'], None)


class GithubHookViewTestCase(APITestCase):
    fixtures = ['complete.json']

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
