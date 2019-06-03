# intended to be sourced into other scripts to set the git environment varaibles
# GIT_COMMIT, GIT_COMMIT_SHORT, DOCKER_IMAGE_TAG.

if [[ -z "$GIT_COMMIT" ]]; then
    export GIT_COMMIT=$(git rev-parse HEAD)
fi

if [[ -z "$DOCKER_REPOSITORY" ]]; then
    export DOCKER_REPOSITORY="mozorg/snippets"
fi

# match length of git rev-parse HEAD --short
export GIT_COMMIT_SHORT="${GIT_COMMIT:0:7}"

if [[ -z "$DOCKER_IMAGE_TAG" ]]; then
    export DOCKER_IMAGE_TAG="${DOCKER_REPOSITORY}:${GIT_COMMIT_SHORT}"
fi
