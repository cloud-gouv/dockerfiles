# docker-k8s-tools

This container image is a toolbox to operate resources on kubernetes cluster.

It can be used to develop or operate cluster stack or inside CI/CD workflows

It includes following tools:
- kubectl 
- helm 
- helmfile 
- mkcert 
- age 
- sops 
- clusterctl
- yq
- argocd cli

## Build
```
docker-compose build
```

## Run in development mode and interact with a local kind cluster

Prereq:
- create a kind cluster (ensure is running)
- $HOME/.kube/config is present
- the container k8s_tools will be connected to the `kind` network to access kube api control plane on private url (`https://IP:6443`)

```
#
# create a kind cluster named "mgmt"

# get kind-mgmt ctrl plane private ip
KUBE_CTRLPLANE_IP=$(docker inspect  -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' mgmt-control-plane)

# replace it in KUBECONFIG
kubectl config set clusters.kind-mgmt.server https://${KUBE_CTRLPLANE_IP}:6443

# start k8s_tools container in shell mode
export DOCKER_REGISTRY=ghcr.io/cloud-gouv/
docker-compose run -i --rm k8s_tools /bin/bash

# Inside container, verify kube api access
kubectl config use-context  kind-mgmt
kubectl get pod -A

```
