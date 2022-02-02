#!/bin/bash

export $(egrep -v '^#' .env)

sed -i.bak \
    -e "s/DOCKER_VERSION_VALUE/${BUILD_VERSION}/g" \
    -e "s/BTE_ALLOWED_HOSTS_VALUE/${BTE_ALLOWED_HOSTS}/g" \
    deployment.yaml
rm deployment.yaml.bak

sed -i.bak \
    -e "s/BTEPA_HOSTNAME_VALUE/${BTEPA_HOSTNAME}/g" \
    -e "s/BTE_ALB_TAG_VALUE/${BTE_ALB_TAG}/g" \
    -e "s/BTE_ALB_SG_VALUE/${BTE_ALB_SG}/g" \
    -e "s/ENVIRONMENT_TAG_VALUE/${ENVIRONMENT_TAG}/g" \
    ingress.yaml
rm ingress.yaml.bak
export ES_HOST=0.0.0.0
kubectl apply -f namespace.yaml
kubectl apply -f deployment.yaml
kubectl apply -f services.yaml
kubectl apply -f ingress.yaml
