#!/bin/bash

set -exo pipefail

BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $BIN_DIR/set_git_env_vars.sh # sets DOCKER_IMAGE_TAG

function imageExists() {
    docker history -q "${DOCKER_IMAGE_TAG}" > /dev/null 2>&1
    return $?
}

if ! imageExists; then
    docker build -t "$DOCKER_IMAGE_TAG" --pull .
fi
