#
# Base image
#
FROM --platform=linux/amd64 debian:bullseye-20260623@sha256:e7100042ddfd3c1fb9d4a5bf15acbdb1058d7bb3340142916d3413a5c001fc89

ARG http_proxy=${http_proxy:-}
ARG https_proxy=${https_proxy:-}
ARG no_proxy=${no_proxy:-}

ARG DEBIAN_PACKAGES="tzdata keyboard-configuration \
      sudo curl git net-tools make gettext-base lsb-release \
      ca-certificates \
      unzip groff less wget vim jq \
      git python3 \
      "

SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]

# get install script
COPY install_tools.sh /build/install_tools.sh

# Install prerequisite packages
RUN export DEBIAN_FRONTEND="noninteractive" \
   ; apt-get -qqy update \
   && apt-get install -qqy ${DEBIAN_PACKAGES} \
   && ln -sf /bin/true /usr/local/bin/docker \
   && echo "export HELM_DATA_HOME=/usr/local/share/helm" > /etc/profile.d/helm.sh \
   ; chmod +x /etc/profile.d/helm.sh \
   ; . /etc/profile.d/helm.sh \
   ; /build/install_tools.sh \
   && kubectl version --client=true \
   && rm -rf /var/lib/apt/lists/* \
   && apt-get -q clean

WORKDIR /data

ENTRYPOINT ["/bin/bash", "-l", "-c"]
