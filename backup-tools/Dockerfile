#
# Base image
#
FROM --platform=linux/amd64 debian:12-slim@sha256:e67eeead736ff7bbe258ef088bff683635c561b1fcfefad0806c1df4ab49ce0e

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
