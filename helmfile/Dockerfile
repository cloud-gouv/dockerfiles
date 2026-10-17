ARG DOCKER_HELMFILE_VERSION=v1.8.2@sha256:4a73ee0e7cca26080ac6c57355bcee0de40b74422ad86e35e08e7dbc558ea9d6

FROM --platform=linux/amd64 ghcr.io/helmfile/helmfile-debian-stable-slim:${DOCKER_HELMFILE_VERSION}

RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
    make \
    && \
    ( curl -L https://carvel.dev/install.sh | sed -e 's/shasum -v/sha256sum --version/g; s/shasum/sha256sum/g' | bash -x ) \
    && \
    rm -rf /var/lib/apt/lists/*
