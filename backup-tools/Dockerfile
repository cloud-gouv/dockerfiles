#
# Base image
#
FROM --platform=linux/amd64 debian:12-slim@sha256:abd67ffcfa541b485a3dff59865ab629aa048a6c613e639d36e7456b0b229241

ARG http_proxy=${http_proxy:-}
ARG https_proxy=${https_proxy:-}
ARG no_proxy=${no_proxy:-}

ARG DEBIAN_PACKAGES="sudo curl unzip"

SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]

# get install script
COPY install_tools.sh /build/install_tools.sh

# Install prerequisite packages
RUN export DEBIAN_FRONTEND="noninteractive" \
   ; apt-get -qqy update \
   && apt-get install -qqy ${DEBIAN_PACKAGES} \
   ; /build/install_tools.sh \
   && rm -rf /var/lib/apt/lists/* \
   && apt-get -q clean

WORKDIR /app
RUN groupadd user \
    && useradd -m -d /app -g user user \
    && chown -R user:user /app
USER user

ENTRYPOINT ["/bin/bash", "-l", "-c"]
