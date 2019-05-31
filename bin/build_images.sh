#!/bin/bash

set -exo pipefail

source set_git_env_vars.sh

function imageExists() {
    docker history -q "${DOCKER_IMAGE_TAG}" > /dev/null 2>&1
    return $?
}

if ! imageExists; then
    docker build -t "$DOCKER_IMAGE_TAG" --pull .
fi
