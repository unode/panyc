#!/usr/bin/env bash

source bash_tap_p.sh

CONFIG="$(get_config default)"


TEST="03-connect_success"
cat ${CONFIG} | run_cmd "${TEST}" -vv | grep "VPN connected successfully"

TEST="03-connect_timeout"
cat ${CONFIG} | (run_cmd "${TEST}" -vv || true) | grep "Connection attempt has timed out"

# vim: ai sts=4 et sw=4
