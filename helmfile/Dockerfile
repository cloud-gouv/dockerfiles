ARG DOCKER_HELMFILE_VERSION=v1.1.9@sha256:08b8aef4e800a3a0ffd6c12246a6a0be8592bf9ec4af92d269d3b0786ada8a6d

FROM --platform=linux/amd64 ghcr.io/helmfile/helmfile-debian-stable-slim:${DOCKER_HELMFILE_VERSION}

RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
    make \
    && \
    ( curl -L https://carvel.dev/install.sh | sed -e 's/shasum -v/sha256sum --version/g; s/shasum/sha256sum/g' | bash -x ) \
    && \
    rm -rf /var/lib/apt/lists/*
