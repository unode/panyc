#!/usr/bin/env bash
. bash_tap_p.sh

CONFIG="$(get_config default)"

# Normal connection
TEST="03-connect_success"
cat ${CONFIG} | run_cmd "${TEST}" -vv connect - | grep "VPN connected and setup successfully"

# Connections fails the first time (simulating bad credentials) but succeeds afterwards
TEST="03-connect_success_retry_one"
cat ${CONFIG} | run_cmd "${TEST}" -vv connect - | grep "VPN connected and setup successfully"

# Connections succeeds but defaults provided by the server differ from provided via config
TEST="03-connect_success_different_prompt"
cat ${CONFIG} | run_cmd "${TEST}" -vv connect - | grep "VPN connected and setup successfully"

# Failed to connect with a server timeout. Simulates loss of internet connection.
TEST="03-connect_timeout"
cat ${CONFIG} | (run_cmd "${TEST}" -vv connect - || true) | grep "Connection attempt has timed out"

# Config is identical to default but contains post-cmd = touch postcmd.touch
CONFIG="$(get_config postcmd)"

TEST="03-connect_success"
TOUCH="postcmd.touch"

# Ensure post-cmd file doesn't exist before the command
[ ! -f "${TOUCH}" ]
# Test that post-cmd creates postcmd.touch
cat ${CONFIG} | run_cmd "${TEST}" -vv connect - | grep "VPN connected and setup successfully"
# Ensure post-cmd created the file as expected
[ -f "${TOUCH}" ]

# vim: ai sts=4 et sw=4
