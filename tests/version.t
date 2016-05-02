#!/usr/bin/env bash
. bash_tap_p.sh

TEST="01-version"

run_cmd "${TEST}" --version -vv | grep "VPN client is version:"

# vim: ai sts=4 et sw=4
