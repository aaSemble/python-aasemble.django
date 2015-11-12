#!/bin/sh
ssh -i deploy.key soren@overcastcloud.com 'cd www; ./deploy.sh ; cd ../dev/current ; ./deploy.sh'
