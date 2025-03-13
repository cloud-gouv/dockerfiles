# backup-tools

This container image is a toolbox to backup to s3

It includes following tools:
- aws-cli
- kubectl 
- clusterctl
- age 
- sops 

## Build
```
docker-compose build
```

## start container in shell mode
```
docker-compose run -i --rm backup_tools
```
