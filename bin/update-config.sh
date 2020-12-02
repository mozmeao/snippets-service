#!/bin/bash
set -ex
# env vars: CLUSTERS, CONFIG_BRANCH, CONFIG_REPO, NAMESPACE
BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

pushd $(mktemp -d)
git clone --depth=1 -b ${CONFIG_BRANCH:=master} ${CONFIG_REPO:=github-mozmar-robot:mozmeao/snippets-config} snippets-config
cd snippets-config

set -u
for CLUSTER in ${CLUSTERS}; do
    for DEPLOYMENT in {web,clock}-deploy.yaml; do
        DEPLOYMENT_FILE=${CLUSTER}/${NAMESPACE}/${DEPLOYMENT}
        if [[ -f ${DEPLOYMENT_FILE} ]]; then
            sed -i -e "s|image: .*|image: ${DOCKER_IMAGE_TAG}|" ${DEPLOYMENT_FILE}
            git add ${DEPLOYMENT_FILE}
        fi
    done
done

cp ${BIN_DIR}/acceptance-tests*.sh .
git add acceptance-tests*.sh
git commit -m "set image to ${DOCKER_IMAGE_TAG}" || echo "nothing new to commit"
git push
popd
