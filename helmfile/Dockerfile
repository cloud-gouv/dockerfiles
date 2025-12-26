ARG DOCKER_HELMFILE_VERSION=v0.171.0

FROM --platform=linux/amd64 ghcr.io/helmfile/helmfile-debian-stable-slim:${DOCKER_HELMFILE_VERSION}

RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
    make \
    && \
    ( curl -L https://carvel.dev/install.sh | sed -e 's/shasum -v/sha256sum --version/g; s/shasum/sha256sum/g' | bash -x ) \
    && \
    rm -rf /var/lib/apt/lists/*
