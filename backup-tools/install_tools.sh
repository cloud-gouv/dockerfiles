#!/bin/bash

set -e -o pipefail

# initArch discovers the architecture for this system.
initArch() {
  ARCH=$(uname -m)
  case $ARCH in
    armv5*) ARCH="armv5";;
    armv6*) ARCH="armv6";;
    armv7*) ARCH="arm";;
    aarch64) ARCH="arm64";;
    x86_64) ARCH="amd64";;
    x86|i686|i386) ARCH="386";;
  esac
}

# initOS discovers the operating system for this system.
initOS() {
  OS=$(uname|tr '[:upper:]' '[:lower:]')
}

# detect OS ARCH
initArch
initOS

# default version
SKIP_INSTALL="${SKIP_INSTALL:-false}"
FORCE_INSTALL="${FORCE_INSTALL:-false}"

# source VERSION
AWS_CLI_VERSION="${AWS_CLI_VERSION:-2.24.22}"
AWS_CLI_URL="https://awscli.amazonaws.com/awscli-exe-${OS}-$(uname -m)${AWS_CLI_VERSION:+-$AWS_CLI_VERSION}.zip"
AWS_CLI_BINARY="awscliv2.zip"
KUBECTL_VERSION="${KUBECTL_VERSION:-stable}"
KUBECTL_RELEASE_VERSION="https://dl.k8s.io/release"
case "$KUBECTL_VERSION" in
    stable) KUBECTL_VERSION="$(curl -Lfs $KUBECTL_RELEASE_VERSION/stable.txt)" ;;
esac
KUBECTL_URL=${KUBECTL_RELEASE_VERSION}/${KUBECTL_VERSION}/bin/${OS}/${ARCH}/kubectl
CLUSTERCTL_VERSION=${CLUSTERCTL_VERSION:-v1.8.10}
CLUSTERCTL_BINARY=clusterctl-${OS}-${ARCH}
CLUSTERCTL_URL="https://github.com/kubernetes-sigs/cluster-api/releases/download/${CLUSTERCTL_VERSION}/${CLUSTERCTL_BINARY}"
SOPS_VERSION="${SOPS_VERSION:-v3.9.4}"
SOPS_BINARY="sops-${SOPS_VERSION}.${OS}.${ARCH}"
SOPS_URL="https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/${SOPS_BINARY}"
AGE_VERSION="${AGE_VERSION:-v1.2.1}"
AGE_URL="https://github.com/FiloSottile/age/releases/download/${AGE_VERSION}/age-${AGE_VERSION}-${OS}-${ARCH}.tar.gz"

if [[ "${SKIP_INSTALL}" == "false" ]]; then
  # default
  aws_cli_is_installed="false"
  kubectl_is_installed="false"
  clusterctl_is_installed="false"
  age_is_installed="false"
  sops_is_installed="false"

  if [[ "${FORCE_INSTALL}" == "false" ]]; then
    # check if exist
    type aws && aws_cli__is_installed="true"
    type kubectl && kubectl_is_installed="true"
    type clusterctl && clusterctl_is_installed="true"
    type age && age_is_installed="true"
    type sops && sops_is_installed="true"

  else
    echo "# force install ${FORCE_INSTALL}"
  fi

  if [[ "$aws_cli_is_installed" == "false" ]];then
    echo "# Install aws ${AWS_CLI_VERSION} from ${AWS_CLI_URL}"
    curl -sSL "${AWS_CLI_URL}" -o "${AWS_CLI_BINARY}"
    unzip ${AWS_CLI_BINARY}
    ./aws/install
    rm -rf ${AWS_CLI_BINARY}
    rm -rf ./aws
    aws --version
  fi

  if [[ "$clusterctl_is_installed" == "false" ]];then
    echo "# Install clusterctl ${CLUSTERCTL_VERSION} from ${CLUSTERCTL_URL}"
    curl -sSLO ${CLUSTERCTL_URL}
    chmod +x ${CLUSTERCTL_BINARY}
    sudo mv ${CLUSTERCTL_BINARY} /usr/local/bin/${CLUSTERCTL_BINARY}
    sudo ln -sf /usr/local/bin/${CLUSTERCTL_BINARY} /usr/local/bin/clusterctl
  fi

  if [[ "$kubectl_is_installed" == "false" ]];then
    echo "# Install kubectl ${KUBECTL_VERSION} from ${KUBECTL_URL}"
    curl -LOs ${KUBECTL_URL}
    chmod +x kubectl
    sudo mv kubectl /usr/local/bin/kubectl
    sudo chmod 755 /usr/local/bin/kubectl
  fi
  echo "# kubectl"
  kubectl version --client
  
  if [[ "$age_is_installed" == "false" ]];then
    echo "# Install age ${AGE_VERSION} from ${AGE_URL}"
    curl -Ls ${AGE_URL} | tar zxvf - age/age age/age-keygen
    sudo mv age/age /usr/local/bin/age
    sudo mv age/age-keygen /usr/local/bin/age-keygen
    sudo chmod 755 /usr/local/bin/age /usr/local/bin/age-keygen
    rm -rf age
  fi
  echo "# age"
  age --version
  age-keygen --version
  
  if [[ "$sops_is_installed" == "false" ]];then
    echo "# Install sops ${SOPS_VERSION} from ${SOPS_URL}"
    curl -LOs ${SOPS_URL}
    chmod +x ${SOPS_BINARY}
    sudo mv ${SOPS_BINARY} /usr/local/bin/sops
    sudo chmod 755 /usr/local/bin/sops
  fi
  echo "# sops"
  sops -version
fi
