#!/bin/sh
ls
pwd
openssl aes-256-cbc -K $encrypted_8f2ce7add2e8_key -iv $encrypted_8f2ce7add2e8_iv -in deploy.key.enc -out deploy.key -d || echo it failed
ls
chmod 600 deploy.key
env | grep -v encrypted
: ssh -i deploy.key -o UserKnownHostsFile=.known_hosts soren@overcastcloud.com 'cd www; ./deploy.sh ; cd ../dev/current ; ./deploy.sh'
