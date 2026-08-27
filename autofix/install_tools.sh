#!/bin/bash

KUBECTL_VERSION=1.35.8 # https://github.com/kubernetes/kubernetes/releases
PYTHON_KUBERNETES_VERSION=35.0.0 # https://pypi.org/project/kubernetes/#history
YQ_VERSION=4.53.6 # https://github.com/mikefarah/yq/releases

set -euxo pipefail

echo "# Deb packages"
export DEBIAN_FRONTEND="noninteractive"
apt-get -qqy update
apt-get install -qqy \
  curl jq \
  python3 python3-pip

echo "# Python packages"
export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore
pip3 install --disable-pip-version-check --break-system-packages kubernetes==$PYTHON_KUBERNETES_VERSION
python3 -c 'import kubernetes; print(kubernetes.__version__)'

echo "# Other packages"
echo "## mikefarah yq"
curl -L -o /usr/bin/yq https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/yq_linux_amd64
chmod +x /usr/bin/yq
yq --version

echo "## kubectl"
curl -LO --output-dir /usr/bin https://dl.k8s.io/release/v$KUBECTL_VERSION/bin/linux/amd64/kubectl
chmod +x /usr/bin/kubectl
kubectl version --client

echo "# Cleanup"
rm -rf /var/lib/apt/lists/*
apt-get -q clean

echo "# Create user"
groupadd autofix
useradd -m -d /home/autofix -g autofix autofix
chown -R autofix:autofix /home/autofix
