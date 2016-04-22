# Panyc

For Python AnyConnect, is a small python wrapper on Cisco's AnyConnect
command-line VPN interface.

This wrapper was created because the provided command line binary has limited
automation functionality making it hard to script in a fault tolerant way.


Its main features are:
    
* Support for multiple connection profiles
* Store all sensitive data on a keychain (passwordstore.org)
* Customize connection after success. Useful for:
    * Altering routing rules
    * Automate waking up of services
    * Anything you can think of...


## Config example

See [the config used for tests](tests/data/default.config)


## Usage

The script can be used by feeding a configuration file via stdin:

    cat tests/data/default.config | ./panyc.py -

or by providing a password store identifier:

    ./panyc.py vpn/myvpn

You can store a config entry in pass by running:

    cat tests/data/default.config | pass insert -m vpn/myvpn

For more information check [the password-store website](https://passwordstore.org).


### Connecting

To start a new connection run:

    ./panyc.py vpn/myvpn

to disconnect:

    ./panyc.py --disconnect

to check the status of the connection:

    ./panyc.py --status

to obtain the version of the VPN client:

    ./panyc.py --version

for anything else:

    ./panyc.py --help
