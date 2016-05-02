#!/usr/bin/env bash

source bash_tap_p.sh

CONFIG="$(get_config default)"


TEST="03-connect_success"
cat ${CONFIG} | run_cmd "${TEST}" -vv connect - | grep "VPN connected successfully"

TEST="03-connect_success_retry_one"
cat ${CONFIG} | run_cmd "${TEST}" -vv connect - | grep "VPN connected successfully"

TEST="03-connect_success_different_prompt"
cat ${CONFIG} | run_cmd "${TEST}" -vv connect - | grep "VPN connected successfully"

TEST="03-connect_timeout"
cat ${CONFIG} | (run_cmd "${TEST}" -vv connect - || true) | grep "Connection attempt has timed out"

# vim: ai sts=4 et sw=4
