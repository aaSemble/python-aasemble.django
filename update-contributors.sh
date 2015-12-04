#!/bin/sh
git log --pretty=format:'%aN <%aE>' | sort -u > CONTRIBUTORS
