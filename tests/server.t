#!/usr/bin/env bash
. bash_tap_p.sh

CONFIG="$(get_config default)"

TEST="00-server_not_running"
cat ${CONFIG} | (run_cmd "${TEST}" -vv connect - || true) | grep "VPN Service is not available"

TEST="00-server_not_running"
(run_cmd "${TEST}" -vv disconnect || true) | grep "VPN Service is not available"

TEST="00-server_not_running"
(run_cmd "${TEST}" -vv status || true) | grep "VPN Service is not available"

# vim: ai sts=4 et sw=4
