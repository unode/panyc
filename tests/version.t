#!/usr/bin/env bash
. bash_tap_p.sh

TEST="01-version"

# Test that both Panyc and VPN client versions are shown
run_cmd "${TEST}" --version -vv | grep -z "Panyc is version:.*VPN client is version:"

# vim: ai sts=4 et sw=4
