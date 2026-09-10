FROM alpine:3.24@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b

COPY install_tools.sh /build/install_tools.sh
RUN /build/install_tools.sh

USER autofix
WORKDIR /home/autofix

