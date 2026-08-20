#
# Base image
#
FROM --platform=linux/amd64 ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517

ARG http_proxy=${http_proxy:-}
ARG https_proxy=${https_proxy:-}
ARG no_proxy=${no_proxy:-}

ARG DEBIAN_PACKAGES="tzdata keyboard-configuration \
      sudo net-tools gettext-base lsb-release \
      build-essential \
      ca-certificates gnupg software-properties-common \
      unzip groff less wget \
      rsync \
      make jq git curl unzip gettext \
      python3 python3-pip \
      pipx \
      mkisofs \
      qemu-system-x86 \
      qemu-kvm \
      qemu-utils \
      rclone \
      xorriso \
      golang-go \
      debsecan \
      "

ARG PIP_PACKAGES="python-openstackclient==7.4.0 \
                  ansible-core==2.21.3 ansible \
                  ansible-lint \
                  "

ARG ANSIBLE_COLLECTIONS="amazon.aws:5.5.0 \
                         community.general:<12.0.0' \
                         ansible.posix \
                         "

SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]

# get install script
COPY install_tools.sh /build/install_tools.sh

# Install prerequisite packages
RUN export DEBIAN_FRONTEND="noninteractive" \
   ; echo "# Deb packages" \
   ; apt-get -qqy update \
   && apt-get install -qqy ${DEBIAN_PACKAGES} \
   ; echo "# Python packages" \
   ; export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore \
   ; pip3 install --disable-pip-version-check --break-system-packages ${PIP_PACKAGES} \
   ; echo "# Ansible packages" \
   ; ansible-galaxy collection install ${ANSIBLE_COLLECTIONS} \
   ; echo "# Other packages" \
   ; /build/install_tools.sh \
   ; echo "# Cleanup" \
   && rm -rf /var/lib/apt/lists/* \
   && apt-get -q clean \
   ; groupadd imagebuilder \
   && useradd -m -d /home/imagebuilder -g imagebuilder imagebuilder \
   && chown -R imagebuilder:imagebuilder /home/imagebuilder

# No entrypoint to avoid having to override it https://docs.gitlab.com/ci/docker/using_docker_images/#override-the-entrypoint-of-an-image
# Gitlab runner expect the use of root user, it will mount the repo as root.
