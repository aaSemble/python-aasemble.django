#!/usr/bin/env python
#
#   Copyright 2015 Reliance Jio Infocomm, Ltd.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
from setuptools import setup, find_packages

with open('requirements.txt', 'r') as fp:
    requirements = []
    for l in fp:
         l = l.strip()
         if '://' in l:
             l = l.split('/')[-1]
             if '#egg=' in l:
                 l = l.split('#egg=')[-1]
         requirements.append(l)

setup(
    name='aasemble.django',
    version='0.1a',
    long_description=__doc__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requirements,
)
