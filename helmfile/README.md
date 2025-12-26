# Dockerfile helmfile for argocd plugin

Including:
- helmfile docker image from https://github.com/helmfile/helmfile/blob/main/Dockerfile.debian-stable-slim
  - helmfile v0.171.0 with helm v3.17.0
  - helmfile v1.1.9 with helm v3.19.0
  - helmfile v1.2.3 with helm v4.0.4
- addons:
  - ytt, kbld from https://carvel.dev

## Build

- ex: Build helmfile v0.171.0
```bash
( export DOCKER_HELMFILE_VERSION=v0.171.0; docker-compose build --build-arg  DOCKER_HELMFILE_VERSION=$DOCKER_HELMFILE_VERSION )
```

- ex: Build helmfile v1.1.9
```bash
 ( export DOCKER_HELMFILE_VERSION=v1.1.9; docker-compose build --build-arg  DOCKER_HELMFILE_VERSION=$DOCKER_HELMFILE_VERSION )
```

- ex: Build helmfile v1.2.3
```bash
 ( export DOCKER_HELMFILE_VERSION=v1.2.3; docker-compose build --build-arg  DOCKER_HELMFILE_VERSION=$DOCKER_HELMFILE_VERSION )
```

