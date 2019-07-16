#!/bin/bash

set -exo pipefail

function imageExists() {
    docker history -q "${DOCKER_IMAGE_TAG}" > /dev/null 2>&1
    return $?
}

if ! imageExists; then
    echo $GIT_COMMIT > revision.txt
    docker build -t "$DOCKER_IMAGE_TAG" --pull .
fi
