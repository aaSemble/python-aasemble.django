import hashlib

from . import github


def get_fileinfo(fpath):
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    size = 0
    with open(fpath, 'rb') as fp:
        while True:
            buf = fp.read(4 * 1024 * 1024)
            md5.update(buf)
            sha1.update(buf)
            sha256.update(buf)
            size += len(buf)
    return {'md5': md5.hexdigest(),
            'sha1': sha1.hexdigest(),
            'sha256': sha256.hexdigest(),
            'size': size}


def sync_sources_from_github(user):
    from ..models import GithubRepository

    current_sources = set([(s.repo_owner, s.repo_name) for s in user.githubrepository_set.all()])
    sources_on_github = {(s['owner']['login'], s['name']): s for s in github.get_repositories(user)}
    new_repos = set(sources_on_github.keys()) - current_sources

    for new_repo in new_repos:
        GithubRepository.create_from_github_repo(user, sources_on_github[new_repo])
