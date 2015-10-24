#import requests

#def github_api_req(path, user):
#    access_token = user.social_auth.all()[0].extra_data['access_token']
#    headers = {'Authorization': 'token %s' % access_token}
#    resp = requests.get('https://api.github.com%s' % path,
#                        headers=headers)
#    return resp
#
#def get_github_user_info(user):
#    return github_api_req('/user', user).json()
#
#def github_is_user_member_of_org(org_name, user):
#    user_info = get_github_user_info(user)
#    resp = github_api_req('/orgs/%s/members/%s' % (org_name, user_info['login']), user)
#    return resp.status_code == 204
#
#def github_get_repos(user):
#    repos = []
#    url = '/user/repos'
#    while True:
#        resp = github_api_req(url, user)
#        repos += resp.json()
#        if 'next' not in resp.links:
#            break
#        url = resp.links['next']['url'][len('https://api.github.com'):]
##    return repos
