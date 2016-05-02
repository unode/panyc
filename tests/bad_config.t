#!/usr/bin/env bash
. bash_tap_p.sh

# Test no or empty config provided via STDIN
TEST="03-connect_success"
cat /dev/null | (run_cmd "${TEST}" -vv connect - || true) | grep "Settings section not found in STDIN"

# This config is missing the host parameter
CONFIG="$(get_config missing)"

# Test that required parameters result in an error
TEST="03-connect_success"
cat ${CONFIG} | (run_cmd "${TEST}" -vv connect - || true) | grep "Missing parameter host for account STDIN"

CONFIG="$(get_config default)"

# Simulate complete failure of authentication after several retries
TEST="05-connect_bad_auth"
cat ${CONFIG} | (run_cmd "${TEST}" -vv connect - || true) | grep "Failed to authenticate. Bad credentials?"

# vim: ai sts=4 et sw=4
