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

# runs the given command as root (detects if we are root already)
runAsRoot() {
  if [ $EUID -ne 0 -a "$USE_SUDO" = "true" ]; then
    sudo "${@}"
  else
    "${@}"
  fi
}

# detect OS ARCH
initArch
initOS

# default version
export INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
export USE_SUDO="${USE_SUDO:-true}"

SKIP_INSTALL="${SKIP_INSTALL:-false}"
FORCE_INSTALL="${FORCE_INSTALL:-false}"

# source VERSION
export AGE_VERSION="${AGE_VERSION:-v1.2.0}"
export AGE_URL="https://github.com/FiloSottile/age/releases/download/${AGE_VERSION}/age-${AGE_VERSION}-${OS}-${ARCH}.tar.gz"
export SOPS_VERSION="${SOPS_VERSION:-v3.8.1}"
export SOPS_BINARY="sops-${SOPS_VERSION}.${OS}.${ARCH}"
export SOPS_URL="https://github.com/getsops/sops/releases/download/${SOPS_VERSION}/${SOPS_BINARY}"
export YQ_VERSION=${YQ_VERSION:-v4.48.2}
export YQ_BINARY=yq_${OS}_${ARCH}
export YQ_URL=https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/${YQ_BINARY}.tar.gz
export TOFU_VERSION="${TOFU_VERSION:-1.10.7}"
export TOFU_BINARY=tofu_${TOFU_VERSION}_${OS}_${ARCH}
export TOFU_URL=https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/${TOFU_BINARY}.tar.gz
export PACKER_VERSION=${PACKER_VERSION:-1.13.1}
export PACKER_ZIP=packer_${PACKER_VERSION}_${OS}_${ARCH}.zip
export PACKER_URL=https://releases.hashicorp.com/packer/${PACKER_VERSION}/${PACKER_ZIP}

if [[ "${SKIP_INSTALL}" == "false" ]]; then
  # default
  yq_is_installed="false"
  age_is_installed="false"
  sops_is_installed="false"
  tofu_is_installed="false"
  packer_is_installed="false"

  if [[ "${FORCE_INSTALL}" == "false" ]]; then
    # check if exist
    type yq && yq_is_installed="true"
    type age && age_is_installed="true"
    type sops && sops_is_installed="true"
    type tofu && tofu_is_installed="true"
    type packer && packer_is_installed="true"
  else
    echo "# force install ${FORCE_INSTALL}"
  fi

  if [[ "$yq_is_installed" == "false" ]];then
    echo "# Install yq ${YQ_VERSION} from ${YQ_URL}"
    curl -sSLO ${YQ_URL}
    tar -zxvf ${YQ_BINARY}.tar.gz  ./${YQ_BINARY}
    rm -rf ${YQ_BINARY}.tar.gz
    chmod +x ${YQ_BINARY}
    runAsRoot mv ${YQ_BINARY} ${INSTALL_DIR}/${YQ_BINARY}
    runAsRoot ln -sf ${INSTALL_DIR}/${YQ_BINARY} ${INSTALL_DIR}/yq
  fi
  if [[ "$age_is_installed" == "false" ]];then
    echo "# Install age ${AGE_VERSION} from ${AGE_URL}"
    curl -Ls ${AGE_URL} | tar zxvf - age/age age/age-keygen
    runAsRoot mv age/age ${INSTALL_DIR}/age
    runAsRoot mv age/age-keygen ${INSTALL_DIR}/age-keygen
    runAsRoot chmod 755 ${INSTALL_DIR}/age ${INSTALL_DIR}/age-keygen
    rm -rf age
  fi
  echo "# age"
  age --version
  age-keygen --version

  if [[ "$sops_is_installed" == "false" ]];then
    echo "# Install sops ${SOPS_VERSION} from ${SOPS_URL}"
    curl -LOs ${SOPS_URL}
    chmod +x ${SOPS_BINARY}
    runAsRoot mv ${SOPS_BINARY} ${INSTALL_DIR}/sops
    runAsRoot chmod 755 ${INSTALL_DIR}/sops
  fi
  echo "# sops"
  sops -version

  if [[ "$tofu_is_installed" == "false" ]];then
    echo "# Install tofu ${TOFU_VERSION} from ${TOFU_URL}"
    curl -Ls ${TOFU_URL} | tar zxvf - tofu
    chmod +x tofu
    runAsRoot mv tofu ${INSTALL_DIR}/tofu
    runAsRoot chmod 755 ${INSTALL_DIR}/tofu
  fi
  echo "# tofu"
  tofu -version

  if [[ "$packer_is_installed" == "false" ]];then
    curl -LO ${PACKER_URL}
    unzip -o ../${PACKER_ZIP} packer
    chmod +x packer
    runAsRoot mv packer ${INSTALL_DIR}/packer
    runAsRoot chmod 755 ${INSTALL_DIR}/packer
    rm -rf ${PACKER_ZIP}
  fi
  packer --version
fi
