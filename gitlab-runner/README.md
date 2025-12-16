# gitlab-runner

This container image is a toolbox to run on gitlab runner

It can be used to run on runner inside CI/CD workflows to build images with packer

It includes following tools:
- jq
- git
- curl
- openstack cli
- rclone
- make
- unzip
- gettext
- mkisofs
- (pipx)
- tofu
- openssl
- qemu-img/qemu-system
- mikefarah/yq
- packer

## Build
```
docker-compose build
```
