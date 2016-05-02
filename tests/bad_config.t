#!/usr/bin/env bash
. bash_tap_p.sh

TEST="03-connect_success"
cat /dev/null | (run_cmd "${TEST}" -vv connect - || true) | grep "Settings section not found in STDIN"

CONFIG="$(get_config missing)"

TEST="03-connect_success"
cat ${CONFIG} | (run_cmd "${TEST}" -vv connect - || true) | grep "Missing parameter host for account STDIN"

CONFIG="$(get_config default)"

TEST="05-connect_bad_auth"
cat ${CONFIG} | (run_cmd "${TEST}" -vv connect - || true) | grep "Failed to authenticate. Bad credentials?"

# vim: ai sts=4 et sw=4
