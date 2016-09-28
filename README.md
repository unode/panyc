# Panyc

For Python AnyConnect, is a small python wrapper on Cisco's AnyConnect
command-line VPN interface. [![Build Status](https://travis-ci.org/Unode/panyc.svg?branch=master)](https://travis-ci.org/Unode/panyc)

This wrapper was created because the provided command line binary has limited
automation functionality making it hard to script in a fault tolerant way.


Its main features are:

* Support for multiple connection profiles
* Store all sensitive data on a keychain (passwordstore.org)
* Customize connection after success. Useful for:
    * Automate waking up of services
    * Anything you can think of...


## Config example

See [one config used for tests](tests/data/postcmd.config)


## Installation

Panyc requirements are included in the `requirements.txt` file.

To install in a virtualenv use:

    pip install -r requirements.txt


## Usage

The script can be used by feeding a configuration file via stdin:

    cat tests/data/default.config | ./panyc.py connect -

or by providing a passwordstore identifier:

    ./panyc.py connect vpn/myvpn

You can a skeleton config to passwordstore (aka pass) by running:

    cat tests/data/default.config | pass insert -m vpn/myvpn

For more information about pass check [the password-store website](https://passwordstore.org).


### Connecting

To start a new connection run:

    ./panyc.py connect vpn/myvpn

to disconnect:

    ./panyc.py disconnect

to check the status of the connection:

    ./panyc.py status

to obtain the version of the VPN client:

    ./panyc.py --version

for anything else:

    ./panyc.py --help
