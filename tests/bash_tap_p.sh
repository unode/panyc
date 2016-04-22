#!/usr/bin/env bash
# This file only contains helper functions for making testing easier.
# The magic happens in bash_tap.sh sourced at the end of this file.
#
# Subject to the MIT License. See LICENSE file or http://opensource.org/licenses/MIT
# Copyright (c) 2016 Renato Alves

function get_config {
    echo "${bashtap_org_pwd}/data/${1}.config"
}

function run_cmd {
    TEST_CONFIG="${1}"
    shift
    ${bashtap_org_pwd}/../panyc.py - --cmd "${bashtap_org_pwd}/helpers/dumbfeed.py ${bashtap_org_pwd}/data/${TEST_CONFIG}.data" "$@"
}

# Include the base script that does the actual work.
source bash_tap.sh
