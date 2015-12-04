# aaSemble API documentation 


### Versioning and base URL:
aaSemble has three API versions. Each API version has its own base URL endpoint. The `v1` endpoint is `https://aasemble.com/api/v1/`, the `v2` endpoint is `https://aasemble.com/api/v2/`, and the `v3` endpoint is `https://aasemble.com/api/v3/`.

When it says `/sources` below, the full URL would be e.g. `https://aasemble.com/api/v1/sources` for the `v1` API. `v1` and `v2` are considered frozen. `v3` is still in development.

## Authentication
In order to authenticate with the API, you need to pass a HTTP header: `Authorization: Token abcdef123456789` where `abcdef123456789` should be replaced with your personal API token. You can find your personal API token under "Profile" on the top menu bar.

## Data model
There are currently 7 data types:
* Sources
* Repositories
* Builds
* External dependencies
* Mirrors
* Mirror sets
* Snapshots

## Sources
A "source" refers to a git repository. It gets polled and whenever there are changes, we build a package and publish it into a "repository".

## Repositories
A "repository" refers to an APT repository that holds packages built from "sources".

## Builds
A "build" is a record of single build of a "source" into a "repository".

## External dependencies
An "external dependency" is another APT repository that will be configured during builds for a given repository so that you can pull build-dependencies from there. There are security risks associated by pulling dependencies from an external APT repository as untested or insecure code may creep into your environment. Use with caution. Ideally try and build everything from a "source" on aaSemble.

## Mirrors
A "mirror" is a mirror of an APT repository. This can be an external APT repository or an aaSemble APT repository.

## Mirror Sets
A "mirror set" is a collection of "mirrors" that are used together.

## Snapshots
A "snapshot" is a point-in-time backup of a "mirror set".

# API reference
The aaSemble API is RESTful API using URIs to identify resources. E.g. `https://aasemble.com/api/v1/mirrors/1/` is the ID of a shared mirror of Ubuntu. The data interchange format is JSON.

## Resource identifiers
The `v1` API uses integers as the final path element in the URI's. `v2` and onwards use UUID's instead.

### HTTP methods
 * `POST` is used to create new resources. E.g. a `POST` request to `/sources/` would  create a new source.
 * `GET` is used to list resources or get details for individual resources. E.g. a `GET` request to `/sources/` would list all sources, while a `GET` request to `/sources/8bc7f6b5-30ce-4fc4-93c9-343614513cd6/` would show only that source.
 * `PUT` is used to replace an object. E.g. a `PUT` request to `/sources/8bc7f6b5-30ce-4fc4-93c9-343614513cd6/` would replace that object with the new one (given in the request body).
 * `PATCH` is used to change a single attribute of an object. Only the attributes given in the request body will be touched, while everything else will be left alone.

### Object types and their attributes

All objects have an attribute called `self` which gives its own ID.

 * `/sources/`:
   * `git_repository`: The URL for the git repository.
   * `git_branch`: The branch to use.
   * `repository`: ID of the repository to publish the built packages into.
   * `builds`: List of builds completed for this source repository.
 * `/repositories/`
   * `user`: Name of the user who owns the repository. You can only see your own repositories as well as repositories that you've explicitly been granted access to. **Read-only**
   * `name`: Name of the repository.
   * `key_id`: The ID of the key generated for this repository.
   * `binary_source_list`: A line for `sources.list` for the binaries (*.deb packages) in this repository (a "deb" line).  **Read-only**
   * `source_source_list`: A line for `sources.list` for the sources in this repository (a "deb-src" line).  **Read-only**
   * `sources`: A URL for the list of sources configured for this repository. **Read-only**
   * `external_dependencies`: A URL for the list of external dependencies configured for this repository. **Read-only**
 * `/external_dependencies/`:
   * `url`: The URL of the remote APT repository.
   * `series`: List of series from the remote APT repository to pull from.
   * `components`: List of components from the remote APT repository to pull from.
   * `repository`: ID of the (local) repository that this external dependency is being added to.
   * `key`: The GPG signing key for the given repository.
 * `/builds/` (**Read-only**):
   * `source`: Up until `v2`: URI of the source that this build relates to. `v3` and onwards embeds the full source resource.
   * `version`: The calculated version of the build.
   * `build_started`: Build start time.
   * `sha`: The revision or commit sha the build was based on.
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
To create a new mirror, send a `POST` request to `http://aasemble.com/api/v3/mirrors/` with the following body:

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
      "self": "https://aasemble.com/api/v3/mirrors/03725ed0-4ed2-427e-9f1f-436009f0d23d/",
    }

So only the "self" attribute is different.

If we want to create a mirror set that includes this mirror, send a `POST` request to `http://aasemble.com/api/v3/mirror_sets/` with the following body:

    {
      "mirrors": ["https://aasemble.com/api/v3/mirrors/03725ed0-4ed2-427e-9f1f-436009f0d23d/"],
    }

The response gives us the ID:

    {
      "mirrors": ["https://aasemble.com/api/v3/mirrors/03725ed0-4ed2-427e-9f1f-436009f0d23d/"],
      "self": "https://aasemble.com/api/v3/mirror_sets/2468b56d-bc8a-4333-8d9a-c2dd94e69a40/"
    }

To create a snapshot, simply send a `POST` request to `http://aasemble.com/api/v3/snapshots/` with the following body:

    {
      "mirrorset": "https://aasemble.com/api/v3/mirror_sets/2468b56d-bc8a-4333-8d9a-c2dd94e69a40/"
    }
