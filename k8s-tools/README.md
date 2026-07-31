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
- store secret age file in  .config/age/secret-age.txt
-  set public age key in PUBLIC_SOPS_AGE environment variable

### Start the  environment
00-run.sh:
    - clone the K8s-tools directory in the  dockerfiles repository
    - create the kind cluster
    - start the docker  with all prerequisite checked
```
sh 00-run.sh
```
In the  docker  execute the  script 01-inside-run.sh

### Start the  environment
00-run.sh:
    - clone the K8s-tools directory in the  dockerfiles repository
    - create the kind cluster
    - start the docker  with all prerequisite checked
```
    sh 00-run.sh
```
### configure the kubectl config
in the docker execute the  following  commande
```
source 01-inside_docker.sh
```

### Clean all
 exit   from the  docker and  exec :
 ```
  sh 10-destroy.sh
 ```