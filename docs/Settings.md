These are the Django settings used to configure aaSemble:

 * `AASEMBLE_BUILDSVC_BUILDER_HTTP_PROXY`: Proxy setting that will get passed to build process. Use this if you're behind a corporate proxy or if you have a caching proxy for speeding up the build process.
 * `AASEMBLE_BUILDSVC_DEFAULT_PARALLEL`: Level of parallelization to use by default. Individual builds can override this in their `.aasemble.yml`, but this allows you to specify a default. It will get passed to `dpkg-buildpackage` as `-jN` where `N` is the value of `AASEMBLE_BUILDSVC_DEFAULT_PARALLEL`. Defaults to 1.
 * `AASEMBLE_BUILDSVC_GCE_KEY_FILE`: The credentials file (in JSON format) for the service account if using Google Compute Engine for builds, 
 * `AASEMBLE_BUILDSVC_GCE_MACHINE_TYPE`: Desired default machine type on Google Compute Engine. Defaults to `n1-standard-4`.
 * `AASEMBLE_BUILDSVC_GCE_PROJECT`: Project name (as seen by Google Compute Engine).
 * `AASEMBLE_BUILDSVC_GCE_SERVICE_ACCOUNT`: Service account e-mail for Google Compute Engine.
 * `AASEMBLE_BUILDSVC_GCE_ZONE`: Desired zone for your build slaves in Google Compute Engine.
 * `AASEMBLE_BUILDSVC_PUBLIC_KEY`: Filename holding the public key you wish to use for authentication with the build slaves. Defaults to `$HOME/.ssh/id_rsa.pub`. The corresponding private key must be available for the Celery workers (so either your Celery workers need to have access to an ssh-agent holding the key, or the private key needs to be unencrypted and in `$HOME/.ssh/id_rsa`)
 * `AASEMBLE_BUILDSVC_USE_WEBHOOKS`: Whether to attempt to use web hooks with Github. This is greatly preferred over polling, but if you're behind a firewall, you're stuck, aren't you?
 * `AASEMBLE_DEFAULT_PROTOCOL`: Default protocol for URL's. This is used in situations where we need to generate a URL, but we're not in the context of an http request that we can use to guess the desired protocol. In practice, this is used whenever a Celery task needs to generate URL (e.g. for passing to build slaves for them to fetch the build details from the webapp).
 * `AASEMBLE_OVERRIDE_NAME`: Override the aaSemble name. Only used in the web UI.
 * `BUILDSVC_DEBEMAIL`: E-mail address to use in generated changelog entries.
 * `BUILDSVC_DEBFULLNAME`: Full name to use in generated changelog entries.
 * `BUILDSVC_DEFAULT_SERIES_NAME`: The name of the series we create for each repository.
 * `BUILDSVC_REPODRIVER`: Name of repository driver. Can be safely ignored.
 * `BUILDSVC_REPOS_BASE_DIR`: Base directory for *private* repository data (i.e. reprepro's internal book keeping stuff).
 * `BUILDSVC_REPOS_BASE_PUBLIC_DIR`: Base directory for *public* repository data.
 * `BUILDSVC_REPOS_BASE_URL`: The base URL corresponding to `BUILDSVC_REPOS_BASE_PUBLIC_DIR`. Since this generally is handled by a web server rather than inside Django, we can't guess it.
 * `MIRRORSVC_BASE_PATH`: The base path for the mirror service.
 * `MIRRORSVC_BASE_URL`: The base URL corresponding to `MIRRORSVC_BASE_PATH`. Like `BUILDSVC_REPOS_BASE_URL`, this is needed because it's typically handled by a web server, not Django.
