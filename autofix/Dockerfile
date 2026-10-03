FROM alpine:3.24@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6

COPY install_tools.sh /build/install_tools.sh
RUN /build/install_tools.sh

USER autofix
WORKDIR /home/autofix

