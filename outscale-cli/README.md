# docker-outscale-cli

[![Docker build and publish](https://github.com/cloud-gouv/dockerfiles/actions/workflows/docker.yml/badge.svg)](https://github.com/cloud-gouv/dockerfiles/actions/workflows/docker.yml)

This repository contains a toolbox to operate resources on [Outscale cloud](https://fr.outscale.com/).
It can be used in CI/CD workflows

Here is tools to build and run a docker image `outscale-cli`, based on `debian:buster` including following tools:
- osc-cli
- osc-sdk-python
- aws
- boto, boto3
- s3cmd
- terraform
- ansible
- packer
- others tools

Docker image is build automatically and available on ghcr.io
  - [ghcr.io/cloud-gouv/outscale-cli](https://github.com/cloud-gouv/dockerfiles/pkgs/container/outscale-cli)

And it can also be build locally and run with docker-compose

Struture directory:
```
- dot-env.sample
- Dockerfile
- docker-compose: build/run image. ./aws, ./osc and current dir are available in the container

- aws/ : .aws config, endpoints and alias, based on `AWS_` variables
  - config
  - models/endpoints.json
  - cli/alias

- osc/
  - osc-cli-wrapper.sh: wrapper which can generate .osc/config.json based on config.json.template based on `OSC_` variables
  - ./config.json.template

- terraform/: sample tf files to build a small vpc, based on `OUTSCALE_` variables
```

## Build

Use docker-compose to build image
```
docker-compose build
```

To override default binaries version, set env variables and build
```bash
DOCKER_OUTSCALE_CLI_VERSION=$DOCKER_OUTSCALE_CLI_VERSION

ANSIBLE_VERSION=$ANSIBLE_VERSION
AWS_CLI_VERSION=$AWS_CLI_VERSION
S3CMD_VERSION=$S3CMD_VERSION
OSC_CLI_VERSION=$OSC_CLI_VERSION
TERRAFORM_VERSION=$TERRAFORM_VERSION
```

## Run

Use docker-compose to use tools in container

PreReq:
- Prepare your env variable,  copy dot-env.sample in .env and Change it!
- use tools with docker-compose

```bash
# copy dot-env.sample .env
# prepare .env with credentials
source .env

# use osc-cli

# use ghcr image
export DOCKER_REGISTRY=ghcr.io/cloud-gouv/
docker-compose run -i --rm cli ./osc/osc-cli-wrapper.sh --help

# use aws
docker-compose run -i --rm cli aws help 

# open a shell in container
docker-compose run -i --rm cli /bin/bash
```

### aws cli

```bash
export AWS_ACCESS_KEY_ID=_CHANGE_KEY_
export AWS_SECRET_ACCESS_KEY=_CHANGE_SECRET_
export AWS_DEFAULT_REGION=_CHANGER_REGION_
```

```bash
docker-compose run -i --rm cli aws ec2 describe-instances

docker-compose run -i --rm cli aws ls-vm
```

### osc-cli

```bash
export OSC_ACCESS_KEY="$AWS_ACCESS_KEY_ID"
export OSC_SECRET_KEY="$AWS_SECRET_ACCESS_KEY"
export OSC_REGION="$AWS_DEFAULT_REGION"
```

```
docker-compose run -i --rm cli ./osc/osc-cli-wrapper.sh api ReadUsers
```

### terraform

```bash
export OUTSCALE_ACCESSKEYID="$AWS_ACCESS_KEY_ID"
export OUTSCALE_SECRETKEYID="$AWS_SECRET_ACCESS_KEY"
export OUTSCALE_REGION="$AWS_DEFAULT_REGION"
```

```
# provider.tf
terraform {
  required_providers {
    outscale = {
      source  = "outscale/outscale"
    }
    cloudinit = {
      source  = "hashicorp/cloudinit"
    }
  }
}

provider "outscale" {
  # Configuration options
  # use env variables from
  #   OUTSCALE_ACCESSKEYID
  #   OUTSCALE_SECRETKEYID
  #   OUTSCALE_REGION
}

```

## Doc reference
Outscale documentation:
- [install osc-cli](https://docs.outscale.com/en/userguide/Installing-and-Configuring-OSC-CLI.html)
- [install aws cli](https://docs.outscale.com/en/userguide/Installing-and-Configuring-AWS-CLI.html)
- [Advanced aws cli](https://docs.outscale.com/en/userguide/Advanced-Use-of-AWS-CLI-for-3DS-OUTSCALE.html)
- [s3cmd](https://docs.outscale.com/en/userguide/s3cmd.html)
- [terraform](https://docs.outscale.com/en/userguide/Terraform.html)
