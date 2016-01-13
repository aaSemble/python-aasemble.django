#!/bin/sh
if [ "$TOX_ENVS" != "py27-django18,py27-django19" ]
then
    # Don't want to run a deploy for each cell in the test matrix
    exit 0
fi

openssl aes-256-cbc -K $encrypted_8f2ce7add2e8_key -iv $encrypted_8f2ce7add2e8_iv -in deploy.key.enc -out deploy.key -d || echo it failed
chmod 600 deploy.key
ssh -i deploy.key -o UserKnownHostsFile=.known_hosts soren@104.197.86.90 'cd srv; cd aasemble/code ; ./deploy.sh ; cd - ; cd overcast/code ; ./deploy.sh'
