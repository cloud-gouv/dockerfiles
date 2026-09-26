DOCKER_MGMT=$(docker ps --format "{{.Names}}")
docker stop $DOCKER_MGMT
docker rm $DOCKER_MGMT
kind delete cluster --name=mgmt
rm -rf k8s-cluster-api-infra
rm -f 01-inside_docker.sh