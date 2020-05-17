#! /usr/bin/env nix-shell
#! nix-shell -p python37Packages.pexpect -i python3
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import argparse
import logging
import pexpect
import shlex
import warnings
from io import StringIO
from subprocess import Popen, call, PIPE
from configparser import RawConfigParser, NoOptionError

__version__ = "0.1"


class Exit(Exception):
    """Exception to allow a clean exit from any point in execution
    """
    SUCCESS = 0
    ERROR = 1
    CONN_TIMEOUT = 2

    BADCONFIG = 10
    BADGROUP = 11
    BADLOGIN = 12

    PREMATURE_END = 50
    TIMEOUT = 51

    def __init__(self, exitcode, msg=None):
        self.exitcode = exitcode
        self.msg = msg

    def __str__(self):
        if self.msg is None:
            return "Abnormal termination with exit code {}".format(self.exitcode)
        else:
            return self.msg


class VPNManager(object):
    def __init__(self, args):
        self.args = args

    def _expect(self, args, **kwargs):
        """Simplify calling pexpect by always handling EOF and TIMEOUT scenarios
        """
        states = [
            pexpect.EOF,
            pexpect.TIMEOUT,
        ]

        if isinstance(args, str):
            states = [args] + states
        else:
            states = list(args) + states

        i = self.p.expect(states, **kwargs)

        shift = len(states)

        if i == shift - 2:
            self.premature_eof()

        elif i == shift - 1:
            self.timeout()

        else:
            return i

    def premature_eof(self):
        raise Exit(Exit.PREMATURE_END, "VPN client finished unexpectedly")

    def timeout(self):
        raise Exit(Exit.TIMEOUT, "VPN client stopped responding")

    def begin(self):
        # With openconnect we start by connecting to the host
        # so we need to read the profile before anything
        self.read_profile()

        LOG.debug("Connecting to %s", self.profile["host"])
        self.p = pexpect.spawn("sudo", [
            self.args.cmd,
            self.profile["host"],
            "--interface", self.profile["interface"] or "tun0",
        ], encoding='utf-8')

        if self.args.verbose >= 2:
            LOG.debug("Enabling subprocess logging to stdout")
            self.p.logfile = sys.stdout

        states = [
            "Connected to HTTPS on",
        ]

        i = self._expect(states)

        if i != 0:
            raise Exit(Exit.ERROR, "Connection was not established")

        LOG.info("Connected to %s", self.profile["host"])

        self.group_select()
        self.authenticate()

        LOG.info("VPN connected, waiting for possible errors")

        states = [
            "Failed to bind local",
            pexpect.TIMEOUT,
        ]

        # NOTE Not using self._expect here since we don't want to fail on timeout
        i = self.p.expect(states, timeout=5)

        if i == 0:
            raise Exit(Exit.ERROR, "Failure to setup interface. Check for permissions")

        LOG.info("No error after 5 seconds, resuming as success")

        post_cmd(self.profile["post_cmd"])

        # Wait until the process ends
        LOG.info("All done, now just keeping an eye on the openconnect process")
        try:
            self.p.wait()
        except KeyboardInterrupt:
            LOG.info("Received Ctrl+C, shutting down VPN")
            self.p.close()

            raise Exit(Exit.SUCCESS, "Exiting after shutdown initiated by user")

        if self.p.exitstatus:
            raise Exit(Exit.ERROR, "VPN finished handshake but exited with error")
        else:
            raise Exit(Exit.SUCCESS, "VPN exited cleanly")

    def read_profile(self):
        """Read and parse profile parameters
        """
        self.profile = get_profile(self.args.profile)

    def group_select(self):
        """Select connection group
        """
        profile = self.profile

        # TODO What if no group is requested?
        states = [
            "GROUP: \\[(.*)\\]:",
        ]

        i = self._expect(states)

        if i == 0:
            group_list = self.p.match.groups()[0].split("|")
            LOG.debug("Group choices %s", group_list)
        elif i == 1:
            raise Exit(Exit.CONN_TIMEOUT, "Connection timed out. Check your internet.")

        if profile["group"] not in group_list:
            raise Exit(Exit.BADGROUP, "Profile provided group is not on the "
                       "list from the server {}".format(group_list))

        LOG.debug("Requesting group %s", profile["group"])
        self.p.sendline(profile["group"])

    def authenticate(self, retry=False):
        """Authenticate against server
        """
        profile = self.profile

        LOG.info("Authenticating...")

        self._expect("Username:")

        LOG.debug("Providing login %s", profile["login"])
        self.p.sendline(profile["login"])

        self._expect("Password:")
        self.p.sendline(profile["password"])

        states = [
            "Established DTLS connection",
            "Authentication failed."
        ]
        i = self._expect(states)

        if i == 0:
            LOG.info("Successfully connected.")
        elif i == 1:
            if retry:
                LOG.info("Login failed after 2 tries. Giving up.")
                raise Exit(Exit.BADLOGIN, "Failed to authenticate. Bad credentials?")
            else:
                LOG.info("Login failed. Retrying...")
                self.authenticate(retry=True)


def post_cmd(command):
    """Run the specified command and wait for it to finish
    """
    if command:
        LOG.info("Running post-cmd: %s", command)
        cmd = shlex.split(command)
        LOG.debug("Post-cmd launched as %s", cmd)

        retcode = call(cmd)

        if retcode != 0:
            warnings.warn("VPN connected but post-cmd exited with non-zero: {}".format(retcode))


def get_profile(profile):
    """Using the provided Read the configuration file and get the connection parameters.
    """
    config = "Settings"
    params = {
        "host": None,       # Host to connect
        "group": None,      # Group used in connection profile
        "login": None,      # Username
        "password": None,
        "interface": None,
        "post_cmd": None,   # Script to execute after connection is established
    }

    if profile == "-":
        LOG.debug("Reading profile from stdin")
        profile = "STDIN"
        data = sys.stdin.read()

        # Convert input to file like object
        configdata = StringIO(data)

    else:
        LOG.debug("Reading profile from password store: %s", profile)
        # Retrieve data from the password store
        p = Popen(["pass", profile], stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()

        if p.returncode != 0:
            sys.stderr.write("Error while reading profile from pass: {!r}\n".format(stderr))
            sys.exit(1)

        # Convert output to file like object
        configdata = StringIO(stdout.decode(sys.stdout.encoding))

    # Parse the config data
    conf = RawConfigParser()
    conf.read_file(configdata)

    # Check if the required section is available in the config file
    if not conf.has_section(config):
        raise Exit(Exit.BADCONFIG, "Settings section not found in {}".format(profile))

    # Read all necessary parameters
    for param in params:
        try:
            params[param] = conf.get(config, param)
        except NoOptionError:
            raise Exit(Exit.BADCONFIG, "Missing parameter {} for account {}".format(
                param, profile))

    return params


def setup_logging(args):
    """Setup the logging level and configure the basic logger
    """
    if args.verbose == 1:
        level = logging.INFO
    elif args.verbose >= 2:
        level = logging.DEBUG
    else:
        # While not fully tested, always run in debug mode so we can capture what went wrong
        # level = logging.WARN
        level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=level,
    )

    global LOG
    LOG = logging.getLogger(__name__)


def parse_sys_args():
    """Parse command line arguments
    """
    class VersionAction(argparse.Action):
        def __call__(self, *args, **kwargs):
            raise Exit(Exit.SUCCESS, "Panyc is version: {}".format(__version__))

    VPN = "/run/current-system/sw/bin/openconnect"
    parser = argparse.ArgumentParser(
        description="Interact with openconnect VPN client"
    )
    parser.add_argument("-c", "--cmd", default=VPN,
                        help="Command and path to launch the vpn binary (default: {})".format(VPN))
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Verbosity level. Warning on -vv (highest level) user input will be printed on screen")

    parser.add_argument("--version", action=VersionAction, nargs=0,
                        help="Print the version of panyc")

    parser.add_argument("profile",
                        help="Name of connection profile (check README) or '-' to read from stdin.")

    args = parser.parse_args()

    return args


def main():
    """Sets up command line parser, message logger and begins interaction
    """
    args = parse_sys_args()
    setup_logging(args)
    LOG.debug(args)

    v = VPNManager(args)
    v.begin()


if __name__ == "__main__":
    try:
        main()
    except Exit as e:
        print(e)
        sys.exit(e.exitcode)

# vim: ai sts=4 et sw=4
