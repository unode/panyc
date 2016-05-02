#!/usr/bin/env bash
. bash_tap_p.sh

TEST="04-disconnect_success"
run_cmd "${TEST}" -vv disconnect | grep "VPN disconnected successfully"

TEST="04-disconnect_not_connected"
(run_cmd "${TEST}" -vv disconnect || true) | grep "VPN is not connected. Cannot disconnect"

# vim: ai sts=4 et sw=4
