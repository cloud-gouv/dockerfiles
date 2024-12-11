#
# Base image
#
FROM --platform=linux/amd64 debian:bookworm

ARG http_proxy=${http_proxy:-}
ARG https_proxy=${https_proxy:-}
ARG no_proxy=${no_proxy:-}
ARG PYPI_URL=${PYPI_URL:-}
ARG PYPI_HOST=${PYPI_HOST:-}

#ARG ANSIBLE_VERSION=${ANSIBLE_VERSION:-2.9.*}
ARG ANSIBLE_VERSION=${ANSIBLE_VERSION:-10.7*}
# install ansible version
# https://docs.ansible.com/ansible/latest/installation_guide/installation_distros.html#installing-ansible-on-debian
#  Debian 12 (Bookworm) -> Ubuntu 22.04 (Jammy) jammy
#  Debian 11 (Bullseye) -> Ubuntu 20.04 (Focal) focal
ARG ANSIBLE_CODENAME=jammy

ARG AWS_CLI_VERSION
ARG OSC_CLI_VERSION
ARG S3CMD_VERSION

ARG TERRAFORM_VERSION=${TERRAFORM_VERSION:-1.5.7*}
#ARG TERRAFORM_VERSION=${TERRAFORM_VERSION:-1.1.0}
#ARG TERRAFORM_VERSION="0.15.3"

# define packages
ARG DEBIAN_PACKAGES="tzdata keyboard-configuration \
      curl unzip groff less wget vim jq sudo \
      gnupg software-properties-common \
      git python3 python3-dnspython python3-redis python3-netaddr python3-jmespath \
      python3-cryptography \
      python3-pip python3-setuptools python3-setuptools python3-urllib3 lsb-release \
      ruby"

# Installing prerequisite packages and ansible
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
RUN . /etc/os-release \
   ; echo "deb http://deb.debian.org/debian ${VERSION_CODENAME}-backports main" > /etc/apt/sources.list.d/${VERSION_CODENAME}-backports.list \
   ; export DEBIAN_FRONTEND="noninteractive" \
   ; apt-get -qqy update \
   && apt-get install -qqy ${DEBIAN_PACKAGES} \
   && apt-get autoremove -y && apt-get autoclean -y \
   && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install ansible version
# https://docs.ansible.com/ansible/latest/installation_guide/installation_distros.html#installing-ansible-on-debian
#  Debian 12 (Bookworm) -> Ubuntu 22.04 (Jammy) jammy
#  Debian 11 (Bullseye) -> Ubuntu 20.04 (Focal) focal
RUN export UBUNTU_CODENAME=$ANSIBLE_CODENAME \
    ; wget -O- "https://keyserver.ubuntu.com/pks/lookup?fingerprint=on&op=get&search=0x6125E2A8C77F2818FB7BD15B93C4A3FD7BB9C367" \
    | sudo gpg --dearmour -o /usr/share/keyrings/ansible-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/ansible-archive-keyring.gpg] http://ppa.launchpad.net/ansible/ansible/ubuntu $UBUNTU_CODENAME main" \
    | tee /etc/apt/sources.list.d/ansible.list \
    && apt-get -qqy update \
    && apt-get install -qqy "ansible${ANSIBLE_VERSION:+=$ANSIBLE_VERSION}" \
    && ansible --version

# install terraform version
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
RUN wget -O - https://apt.releases.hashicorp.com/gpg \
    | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/hashicorp.list \
    ; apt-get -qqy update \
    && apt-get install -qy terraform=${TERRAFORM_VERSION} \
    && terraform --version

# install terraform provider
#COPY provider.tf .
#SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
#RUN mkdir -p /usr/local/share/terraform/plugins && \
#      echo 'plugin_cache_dir = "/usr/local/share/terraform/plugins"' > $HOME/.terraformrc && \
#      terraform init -backend=false

# AWS CLI installation commands
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
RUN	curl -L "https://awscli.amazonaws.com/awscli-exe-linux-x86_64${AWS_CLI_VERSION:+-$AWS_CLI_VERSION}.zip" -o "awscliv2.zip" \
  && unzip awscliv2.zip \
  && ./aws/install \
  && rm awscliv2.zip \
  && aws --version

# install:
#   s3cmd cli
#   Outscale osc-cli
SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]
RUN  pip_args="" ; [ -z "$PYPI_URL" ] || pip_args=" --index-url $PYPI_URL " \
    ; [ -z "$PYPI_HOST" ] || pip_args="$pip_args --trusted-host $PYPI_HOST " \
    ; echo "$no_proxy" |tr ',' '\n' | sort -u |grep "^$PYPI_HOST$" \
    || [ -z "$http_proxy" ] || pip_args="$pip_args --proxy $http_proxy " \
    ; pip3 install --break-system-packages \
        "s3cmd${S3CMD_VERSION:+==$S3CMD_VERSION}" \
        "osc-sdk${OSC_CLI_VERSION:+==$OSC_CLI_VERSION}" \
        osc-sdk-python \
        boto \
        boto3 \
    && s3cmd --help \
    && osc-cli -- --help

WORKDIR /data
