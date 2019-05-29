#!/bin/bash
set -ex

source set_git_env_vars.sh

# Push to docker hub
docker push $DOCKER_IMAGE_TAG