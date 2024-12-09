#!/bin/bash

set -e -o pipefail

#
# install prereq binaries and an empty kind cluster
# This cluster must be configured to bootstrap other clusters
#
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
export KIND_VERSION="${KIND_VERSION:-v0.24.0}"
export KUBECTL_VERSION="${KUBECTL_VERSION:-v1.29.8}"
#export KUBECTL_VERSION="$(curl -Lfs $KUBECTL_RELEASE_VERSION/stable.txt)"
export KUBERNETES_VERSION=${KUBERNETES_VERSION:-v1.29.8}
export HELM_VERSION="${HELM_VERSION:-v3.16.1}"
export HELMFILE_VERSION="${HELMFILE_VERSION:-0.168.0}"
export MKCERT_VERSION="${MKCERT_VERSION:-v1.4.4}"
export AGE_VERSION="${AGE_VERSION:-v1.2.0}"
export SOPS_VERSION="${SOPS_VERSION:-v3.8.1}"

export CLUSTERCTL_VERSION=${CLUSTERCTL_VERSION:-v1.8.4}
export CLUSTERCTL_BINARY=clusterctl-${OS}-${ARCH}
export CLUSTERCTL_URL=https://github.com/kubernetes-sigs/cluster-api/releases/download/${CLUSTERCTL_VERSION}/${CLUSTERCTL_BINARY}

export YQ_VERSION=${YQ_VERSION:-v4.44.3}
export YQ_BINARY=yq_${OS}_${ARCH}
export YQ_URL=https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/${YQ_BINARY}.tar.gz

export ARGOCD_CLI_VERSION=${ARGOCD_CLI_VERSION:-v2.13.1} # Select desired TAG from https://github.com/argoproj/argo-cd/releases
export ARGOCD_CLI_BINARY=argocd-${OS}-${ARCH}
export ARGOCD_CLI_URL=https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_CLI_VERSION}/${ARGOCD_CLI_BINARY}

if [[ "${SKIP_INSTALL}" == "false" ]]; then
  # install some tools (kind, kubectl, helm...)
  echo "Install numerique-gouv/dk8s tools"
  curl -L https://raw.githubusercontent.com/numerique-gouv/dk8s/main/scripts/install-prereq.sh | bash

  # default
  clusterctl_is_installed="false"
  yq_is_installed="false"
  argocd_is_installed="false"

  if [[ "${FORCE_INSTALL}" == "false" ]]; then
    # check if exist
    type clusterctl && clusterctl_is_installed="true"
    type yq && yq_is_installed="true"
    type argocd && argocd_is_installed="true"
  else
    echo "# force install ${FORCE_INSTALL}"
  fi

  if [[ "$clusterctl_is_installed" == "false" ]];then
    echo "# Install clusterctl ${CLUSTERCTL_VERSION} from ${CLUSTERCTL_URL}"
    curl -sSLO ${CLUSTERCTL_URL}
    chmod +x ${CLUSTERCTL_BINARY}
    sudo mv ${CLUSTERCTL_BINARY} /usr/local/bin/${CLUSTERCTL_BINARY}
    sudo ln -sf /usr/local/bin/${CLUSTERCTL_BINARY} /usr/local/bin/clusterctl
  fi

  if [[ "$yq_is_installed" == "false" ]];then
    echo "# Install yq ${YQ_VERSION} from ${YQ_URL}"
    curl -sSLO ${YQ_URL}
    tar -zxvf ${YQ_BINARY}.tar.gz  ./${YQ_BINARY}
    rm -rf ${YQ_BINARY}.tar.gz
    chmod +x ${YQ_BINARY}
    sudo mv ${YQ_BINARY} /usr/local/bin/${YQ_BINARY}
    sudo ln -sf /usr/local/bin/${YQ_BINARY} /usr/local/bin/yq
  fi

  if [[ "$argocd_is_installed" == "false" ]];then
    echo "# Install argocd ${ARGOCD_CLI_VERSION} from ${ARGOCD_CLI_URL}"
    curl -sSLO ${ARGOCD_CLI_URL}
    chmod +x ${ARGOCD_CLI_BINARY}
    sudo mv ${ARGOCD_CLI_BINARY} /usr/local/bin/${ARGOCD_CLI_BINARY}
    sudo ln -sf /usr/local/bin/${ARGOCD_CLI_BINARY} /usr/local/bin/argocd
  fi
fi


