FROM alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf

COPY install_tools.sh /build/install_tools.sh
RUN /build/install_tools.sh

USER autofix
WORKDIR /home/autofix

