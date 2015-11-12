#!/bin/sh
ssh -i deploy.key -o UserKnownHostsFile=.known_hosts soren@overcastcloud.com 'cd www; ./deploy.sh ; cd ../dev/current ; ./deploy.sh'
