import github


def sync_sources_from_github(user):
    from ..models import GithubRepository

    current_sources = set([(s.repo_owner, s.repo_name) for s in user.githubrepository_set.all()])
    sources_on_github = {(s['owner']['login'], s['name']): s for s in github.get_repositories(user)}
    new_repos = set(sources_on_github.keys()) - current_sources

    for new_repo in new_repos:
        GithubRepository.create_from_github_repo(user, sources_on_github[new_repo])
