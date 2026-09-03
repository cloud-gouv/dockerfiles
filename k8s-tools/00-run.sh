# Crée le cluster et export les  
# ce script a pour but d automatiser la  configuration de l environnement pour
# la construction du cluster de management
## prerequis
## avoir le  fichier age-secret stocké en local .config/age/secret-age.txt
## SOPS_AGE_RECIPIENTS dans les variables  d'environnement

# extract only  the  deploy  directory  uncomment  the following line
#git clone --filter=blob:none --sparse git@github.com:cloud-gouv/k8s-cluster-api-infra.git
git clone git@github.com:cloud-gouv/k8s-cluster-api-infra.git
cd k8s-cluster-api-infra
# extract only  the  deploy  directory  uncomment  the following lines
#git sparse-checkout init --cone
#git sparse-checkout set deploy
cp $HOME/.config/age/secret-age.txt deploy/ci-keys.txt
docker-compose build 		  
kind create cluster --name mgmt
export KUBE_CTRLPLANE_IP=$(docker inspect  -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' mgmt-control-plane)
kubectl config set clusters.kind-mgmt.server "https://${KUBE_CTRLPLANE_IP}:6443"
export DOCKER_REGISTRY=ghcr.io/cloud-gouv/
cd ../
pwd
echo "kubectl config use-context  kind-mgmt" > 01-inside_docker.sh
echo "kubectl get nodes" >> 01-inside_docker.sh
echo 'cp k8s-cluster-api-infra/deploy/ci-keys.txt $HOME/ci-key.txt'>>01-inside_docker.sh
echo 'export SOPS_AGE_KEY_FILE="$HOME/ci-keys.txt"'>>01-inside_docker.sh
echo "export SOPS_AGE_RECIPIENTS=$PUBLIC_SOPS_AGE" >> 01-inside_docker.sh
echo "cd k8s-cluster-api-infra/deploy">> 01-inside_docker.sh
docker-compose run -i --rm k8s_tools /bin/bash