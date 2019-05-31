# intended to be sourced into other scripts to set the git environment varaibles
# GIT_COMMIT, GIT_COMMIT_SHORT, DOCKER_IMAGE_TAG.

if [[ -z "$GIT_COMMIT" ]]; then
    export GIT_COMMIT=$(git rev-parse HEAD)
fi
export GIT_COMMIT_SHORT="${GIT_COMMIT:0:9}"
if [[ -z "$DOCKER_REPOSITORY" ]]; then
    export DOCKER_REPOSITORY="mozmeao/nucleus"
fi
if [[ -z "$DOCKER_IMAGE_TAG" ]]; then
    # we are probably going to switch to using GIT_COMMIT_SHORT in the image tag
    export DOCKER_IMAGE_TAG="${DOCKER_REPOSITORY}:${GIT_COMMIT}"
fi
