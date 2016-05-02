#!/usr/bin/env bash
. bash_tap_p.sh

# Status when connected
TEST="02-status_connected"
run_cmd "${TEST}" -vv status | grep "VPN is connected"

# Status when disconnected
TEST="02-status_disconnected"
(run_cmd "${TEST}" -vv status || true) | grep "VPN is not connected"

# vim: ai sts=4 et sw=4
