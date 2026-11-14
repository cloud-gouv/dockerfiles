ARG DOCKER_HELMFILE_VERSION=v1.8.4@sha256:73e6be84b216d474431943d9faf99f3d7572891dab34fa4af8e730730ff366c6

FROM --platform=linux/amd64 ghcr.io/helmfile/helmfile-debian-stable-slim:${DOCKER_HELMFILE_VERSION}

RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
    make \
    && \
    ( curl -L https://carvel.dev/install.sh | sed -e 's/shasum -v/sha256sum --version/g; s/shasum/sha256sum/g' | bash -x ) \
    && \
    rm -rf /var/lib/apt/lists/*
