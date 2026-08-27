FROM debian:13-slim

COPY install_tools.sh /build/install_tools.sh
RUN /build/install_tools.sh

USER autofix
WORKDIR /home/autofix

