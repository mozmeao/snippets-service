#!/bin/bash

set -exo pipefail

BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $BIN_DIR/set_git_env_vars.sh # sets DOCKER_IMAGE_TAG

docker run ${DOCKER_IMAGE_TAG} flake8 snippets
