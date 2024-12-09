#!/bin/bash
#
# osc-cli wrapper
#   generate $HOME/.osc/config.json based on osc/config.json.template and env variables
#   env: OSC_ACCESS_KEY OSC_SECRET_KEY OSC_REGION
#
set -e -o pipefail
OSC_CONFIG_TEMPLATE_FILE="$(dirname $0)"

# generate config.json if file does not exists
if [[ ! -f "$HOME/.osc/config.json" ]] ; then
  [[ -x "$(which jq)" ]] || exit 1
  [[ -v OSC_ACCESS_KEY && -v OSC_SECRET_KEY && -v OSC_REGION ]] || exit 1
  [[ -d "$HOME/.osc" ]] || mkdir -p "$HOME/.osc"

  jq -re '{"default":{"access_key":env.OSC_ACCESS_KEY,"secret_key":env.OSC_SECRET_KEY,"host":.default.host,"https":.default.https,"method":.default.method,"region_name":env.OSC_REGION}}' < $OSC_CONFIG_TEMPLATE_FILE/config.json.template > $HOME/.osc/config.json
fi

osc-cli $@
