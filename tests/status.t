#!/usr/bin/env bash

source bash_tap_p.sh

CONFIG="$(get_config default)"

TEST="02-status_connected"
cat ${CONFIG} | run_cmd "${TEST}" --status -vv | grep "VPN is connected"

TEST="02-status_disconnected"
cat ${CONFIG} | (run_cmd "${TEST}" --status -vv || true) | grep "VPN is not connected"

# vim: ai sts=4 et sw=4
