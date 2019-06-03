#!/bin/bash
set -ex
# env vars: CLUSTER_NAME, CONFIG_BRANCH, CONFIG_REPO, NAMESPACE, DEPLOYMENT_YAML

BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $BIN_DIR/set_git_env_vars.sh # sets DOCKER_IMAGE_TAG

pushd $(mktemp -d)
git clone --depth=1 -b ${CONFIG_BRANCH:=master} ${CONFIG_REPO:=github-mozmar-robot:mozmeao/snippets-config} snippets-config
cd snippets-config

set -u
sed -i -e "s|image: .*|image: ${DOCKER_IMAGE_TAG}|" ${CLUSTER_NAME:=oregon-b}/${NAMESPACE:=snippets-dev}/${DEPLOYMENT_YAML:=deploy.yaml}
git add ${CLUSTER_NAME}/${NAMESPACE}/${DEPLOYMENT_YAML}
git commit -m "set image to ${DOCKER_IMAGE_TAG} in ${CLUSTER_NAME}" || echo "nothing new to commit"
git push
popd
