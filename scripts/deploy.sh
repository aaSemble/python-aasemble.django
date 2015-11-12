#!/bin/sh
if [ "$DJANGO_VERSION" != "1.8" ] || [ "$TRAVIS_PYTHON_VERSION" != "2.7" ]
then
    # Don't want to run a deploy for each cell in the test matrix
    exit 0
fi

openssl aes-256-cbc -K $encrypted_8f2ce7add2e8_key -iv $encrypted_8f2ce7add2e8_iv -in deploy.key.enc -out deploy.key -d || echo it failed
chmod 600 deploy.key
ssh -i deploy.key -o UserKnownHostsFile=.known_hosts soren@overcastcloud.com 'cd www; ./deploy.sh ; cd ../dev/current ; ./deploy.sh'
