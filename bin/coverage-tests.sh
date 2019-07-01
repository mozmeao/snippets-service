#!/bin/bash

set -exo pipefail

BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $BIN_DIR/set_git_env_vars.sh # sets DOCKER_IMAGE_TAG

docker run -e 'DEBUG=False' \
           -e 'ALLOWED_HOSTS=*' \
           -e 'SECRET_KEY=foo' \
           -e 'DATABASE_URL=sqlite:///' \
           -e 'SITE_URL=http://localhost:8000' \
           -e 'CACHE_URL=dummy://' \
           -e 'ENABLE_ADMIN=True' \
           -e 'SECURE_SSL_REDIRECT=False' \
           ${DOCKER_IMAGE_TAG} \
           coverage run ./manage.py test --parallel
