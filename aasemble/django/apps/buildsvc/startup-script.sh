#!/bin/bash

apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
echo 'deb https://apt.dockerproject.org/repo ubuntu-trusty main' > /etc/apt/sources.list.d/docker.list
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python-pip libffi-dev libssl-dev python-dev git docker-engine libmysqlclient-dev
adduser ubuntu docker
cat <<EOF > /root/requirements.txt
PyYAML
Django
python-debian
djangorestframework
git+https://github.com/aaSemble/python-dbuild#egg=dbuild
git+https://github.com/aaSemble/python-aasemble.django
chardet
pytz
docker-py
apache-libcloud
pycrypto
paramiko
EOF
pip install -U -r /root/requirements.txt
