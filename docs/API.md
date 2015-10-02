# aaSemble API documentation
### Base URL:
The base URL is `https://aasemble.com/api/v1`. So, when it says `/sources` below, the full URL would be `https://aasemble.com/api/v1/sources`. Although the path has `v1` in it, the API has not yet been frozen. Once the first revision is relatively stable, we'll tag it `v1` and hope to maintain the API over time.

There are currently 7 data types:
* Sources
* Repositories
* Builds
* External dependencies
* Mirrors
* Mirror sets
* Snapshots

## Repositories
A "repository" refers to an APT repository that holds packages built from "sources".

## Sources
A "source" refers to a git repository. It gets polled and whenever there are changes, we build a package and publish it into a "repository".

## Builds
A "build" is a record of single build of a "source" into a "repository".

## External dependencies
An "external dependency" is another APT repository that will be configured during builds for a given repository so that you can pull build-depencies from there.

## Mirrors
A "mirror" is a mirror of an external APT repository.

## Mirror Sets
A "mirror set" is a collection of "mirrors" that are used together.

## Snapshots
A "snapshot" is a point-in-time backup of a "mirror set".

# API reference
The aaSemble API is RESTful API using URIs to identify resources. E.g. `https://aasemble.com/api/v1/mirrors/1/` is the ID of a shared mirror of Ubuntu. The data interchange format is JSON.

### HTTP methods
 * `POST` is used to create new resources. E.g. a `POST` request to `/sources/` would  create a new source.
 * `GET` is used to list resources or get details for individual resources. E.g. a `GET` request to `/sources/` would list all sources, while a `GET` request to `/sources/44/` would show only that source.
 * `PUT` is used to replace an object. E.g. a `PUT` request to `/sources/44/` would replace that object with the new one (given in the request body).
 * `PATCH` is used to change a single attribute of an object. Only the attributes given in the request body will be touched, while everything else will be left alone.

### Object types and their attributes

All objects have an attribute called `self` which gives its own ID.

 * `/repositories/`
   * `user`: Name of the user who owns the repository. You can only see your own repositories as well as repositories that you've explicitly been granted access to. **Read-only**
   * `name`: Name of the repository.
   * `key_id`: The ID of the key generated for this repository.
   * `binary_source_list`: A line for `sources.list` for the binaries (*.deb packages) in this repository (a "deb" line).  **Read-only**
   * `source_source_list`: A line for `sources.list` for the sources in this repository (a "deb-src" line).  **Read-only**
   * `sources`: A URL for the list of sources configured for this respository. **Read-only**
   * `external_dependencies`: A URL for the list of sources configured for this respository. **Read-only**
 * `/external_dependencies/`:
   * `url`: The URL of the remote APT repository.
   * `series`: List of series from the remote APT repository to pull from.
   * `components`: List of components from the remote APT repository to pull from.
   * `repository`: ID of the (local) repository that this external dependency is being added to.
   * `key`: The GPG signing key for the given repository.
 * `/sources/`:
   * `git_repository`: The URL for the git repository.
   * `git_branch`: The branch to use.
   * `repository`: ID of the repository to publish the built packages into.
 * `/builds/` (**Read-only**):
   * `source`: ID of the source that this build relates to.
   * `version`: The calculated version of the build.
   * `build_started`: Build start time.
   * `sha`: The revision the build was based on.
   * `buildlog_url`: URL for log of the build.
 * `/mirrors/`:
   * `url`: Base URL of the remote repository. E.g. "`http://archive.ubuntu.com/ubuntu`".
   * `series`: List of series to mirror.
   * `components`: List of components to mirror.
   * `public`: Whether or not to share this mirror with other users.
   * `refresh_in_progress`: Boolean denoting whether a refresh is progress. 
 * `/mirror_sets/`:
   * `mirrors`: The list of mirrors to include in this mirror set.
 * `/snapshots/`:
   * `timestamp`: Then the snapshot was started. **Read-only**
   * `mirrorset`: ID of the mirrorset used for the snapshot.

## Extra actions

Some actions don't easily fit the RESTful API style. The aaSemble API currently has only one such action: Refreshing a mirror. It is triggered by sending a `POST` request to `/mirrors/<id>/refresh/`.


## Examples
To create a new mirror, send a `POST` request to `http://aasemble.com/api/v1/mirrors/` with the following body:

    {
      "url": "http://archive.ubuntu.com/ubuntu",
      "series": ["trusty", "trusty-updates", "trusty-security"],
      "components": ["main", "restricted", "universe"],
      "public": true
    }

The response will be something like:

    {
      "url": "http://archive.ubuntu.com/ubuntu",
      "series": ["trusty", "trusty-updates", "trusty-security"],
      "components": ["main", "restricted", "universe"],
      "public": true,
      "self": "https://aasemble.com/api/v1/mirrors/1/",
    }

So only the "self" attribute is different.

If we want to create a mirror set that includes this mirror, send a `POST` request to `http://aasemble.com/api/v1/mirror_sets/` with the following body:

    {
      "mirrors": ["https://aasemble.com/api/v1/mirrors/1/"],
    }

The response gives us the ID:

    {
      "mirrors": ["https://aasemble.com/api/v1/mirrors/1/"],
      "self": "https://aasemble.com/api/v1/mirror_sets/1/"
    }

To create a snapshot, simply send a `POST` request to `http://aasemble.com/api/v1/snapshots/` with the following body:

    {
      "mirrorset": "https://aasemble.com/api/v1/mirror_sets/1/"
    }
