#!/bin/bash

projectName="pendingapi"
namespace="bte"

export $(egrep -v '^#' .env)

sed -i.bak \
    -e "s/DOCKER_VERSION_VALUE/${BUILD_VERSION}/g" \
    values.yaml
rm values.yaml.bak

helm -n ${namespace} upgrade --install ${projectName} -f values-ncats.yaml ./
