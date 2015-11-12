#!/bin/sh
ls
pwd
chmod 600 deploy.key
ssh -i deploy.key -o UserKnownHostsFile=.known_hosts soren@overcastcloud.com 'cd www; ./deploy.sh ; cd ../dev/current ; ./deploy.sh'
