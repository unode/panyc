#!/usr/bin/env bash

source bash_tap_p.sh

CONFIG="$(get_config default)"


TEST="04-disconnect_success"
cat ${CONFIG} | run_cmd "${TEST}" -d -vv | grep "VPN disconnected successfully"

TEST="04-disconnect_not_connected"
cat ${CONFIG} | (run_cmd "${TEST}" -d -vv || true) | grep "VPN is not connected. Cannot disconnect"

# vim: ai sts=4 et sw=4
