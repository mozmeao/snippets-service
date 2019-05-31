#!/bin/bash
set -ex

BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $BIN_DIR/set_git_env_vars.sh # sets DOCKER_IMAGE_TAG

# Push to docker hub
docker push $DOCKER_IMAGE_TAG