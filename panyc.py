#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import argparse
import logging
import pexpect
import shlex
from io import StringIO
from subprocess import Popen, call, PIPE
from configparser import RawConfigParser, NoOptionError

__version__ = "0.1"


class Exit(Exception):
    """Exception to allow a clean exit from any point in execution
    """
    SUCCESS = 0
    ERROR = 1
    NOAGENT = 2
    CONN_TIMEOUT = 3
    ALREADY = 4

    BADCONFIG = 10
    BADGROUP = 11
    BADLOGIN = 12

    ERRAFTER = 20

    PREMATURE_END = 50
    TIMEOUT = 51

    OOPS = 100

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
        self.p = pexpect.spawnu(self.args.cmd)

        if self.args.verbose >= 2:
            LOG.debug("Enabling subprocess logging to stdout")
            self.p.logfile = sys.stdout

        states = [
            "VPN Service is not available",
            "registered with local VPN subsystem",
        ]

        i = self._expect(states)

        if i == 0:
            raise Exit(Exit.NOAGENT, "VPN agent 'vpnagentd' is not running")

        LOG.info("vpnagentd is online.")

        # User requested only the version of the VPN client
        if self.args.version:
            LOG.info("Obtaining version...")
            # NOTE: If the VPN binary/client is called with "vpn -s" and user asks for version,
            # interaction is broken and the process stops accepting input causing it to hang and timeout.
            version = self.version()
            self.exit()

            raise Exit(Exit.SUCCESS, "Panyc is version: {}\nVPN client is version: {}".format(__version__, version))

        # User requested only the status of the connection
        if self.args.action == "status":
            LOG.info("Obtaining connection status...")
            state = self.state()
            self.exit()

            if state:
                raise Exit(Exit.SUCCESS, "VPN is connected")
            else:
                raise Exit(Exit.ERROR, "VPN is not connected")

        # User requested that we would disconnect
        elif self.args.action == "disconnect":
            LOG.info("Disconnecting...")
            self.disconnect()
            self.exit()

            LOG.info("VPN disconnected successfully")

            raise Exit(Exit.SUCCESS, "VPN disconnected successfully")

        else:
            # If we are going to connect, check if we are not already connected to somewhere
            if self.state():
                raise Exit(Exit.ALREADY, "VPN is already connected. Disconnect first")

            # Ok we are good to go!
            LOG.info("Starting connection...")
            self.read_profile()
            self.connect()
            self.authenticate()

            if not self.state():
                raise Exit(Exit.OOPS, "VPN should be connected but is not. Something went wrong.")

            self.exit()

            LOG.info("VPN connected successfully")

            post_cmd(self.profile["post_cmd"])

            raise Exit(Exit.SUCCESS, "VPN connected and setup successfully")

    def read_profile(self):
        """Read and parse profile parameters
        """
        self.profile = get_profile(self.args.profile)

    def connect(self):
        """Connect to server
        """
        self.p.sendline("connect {0}".format(self.profile["host"]))

        self._expect("contacting host")

    def authenticate(self, retry=False):
        """Authenticate against server
        """
        LOG.info("Authenticating...")

        profile = self.profile

        # TODO What if no group is requested?
        if retry:
            states = ["(.*)Group: \[(.*)\]"]
        else:
            states = ["Please enter your username and password\.(.*)Group: \[(.*)\]"]

        # Check if we didn't get a connection timeout for being unable to reach the server
        states.extend([
            "Connection attempt has timed out.",
            pexpect.TIMEOUT,
        ])

        i = self._expect(states)

        if i == 0:
            group_list, default_group = self.p.match.groups()
            LOG.debug("%s is the default group", default_group)

        elif i == 1:
            raise Exit(Exit.CONN_TIMEOUT, "Connection timed out. Check your internet.")

        # If the profile group is the same as default just keep going
        if profile["group"] == default_group:
            LOG.debug("Going with default group")
            self.p.sendline()

        # Otherwise map group names to group IDs.
        # In the prompt we need to provide the group ID
        else:
            LOG.debug("Obtaining group id from: %r", group_list)
            groups = {}
            for line in group_list.splitlines():
                line = line.strip()

                if not line:
                    continue

                LOG.debug("Parsing line %r", line)
                _id, name = line.split(") ")
                groups[name] = _id

            if profile["group"] not in groups:
                raise Exit(Exit.BADGROUP, "Profile provided group is not on the "
                           "list from the server {}".format(groups))

            LOG.debug("Groups parsed: %s", groups)

            groupid = groups[profile["group"]]

            LOG.debug("Using ID %s for group %s", groupid, profile["group"])
            self.p.sendline(groupid)

        self._expect("Username: \[(.*)\]")
        default_login, = self.p.match.groups()

        # Go with default login
        if profile["login"] == default_login:
            LOG.debug("Going with default login")
            self.p.sendline()

        else:
            LOG.debug("Providing login %s", profile["login"])
            self.p.sendline(profile["login"])

        # Password handling
        self._expect("Password: ")
        self.p.sendline(profile["password"])

        states = [
            ">> state: Connected",
            ">> Login failed"
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

    def state(self):
        """Return True if connected and False if disconnected

        If the state is unknown for some reason, it will most likely timeout
        """
        self._expect("VPN> ")
        self.p.sendline("state")
        states = [
            ">> state: Disconnected",
            ">> state: Connected",
        ]
        # We get states[0] or states[1] which match False/True for disconnected/connected
        return bool(self._expect(states))

    def disconnect(self):
        """Disconnect if a connection is already active
        """
        if self.state():
            self._expect("VPN> ")
            self.p.sendline("disconnect")
            self._expect("state: Disconnected")

            if self.state():
                raise Exit(Exit.OOPS, "VPN failed to disconnect. Something went wrong.")
        else:
            raise Exit(Exit.ALREADY, "VPN is not connected. Cannot disconnect")

    def version(self):
        """Return the version of the VPN client
        """
        self._expect("VPN> ")
        self.p.sendline("version")

        self._expect("Client \(version ([0-9\.]*)\) \.")
        client_version, = self.p.match.groups()

        LOG.debug("Obtained version %s", client_version)

        return client_version

    def exit(self):
        """Exist the VPN client
        """
        self._expect("VPN> ")
        self.p.sendline("exit")
        self._expect("goodbye\.\.\.")


def post_cmd(command):
    """Run the specified command and wait for it to finish
    """
    if command:
        cmd = shlex.split(command)
        LOG.debug("Running post-cmd %s", cmd)

        retcode = call(cmd)

        if retcode != 0:
            raise Exit(Exit.ERRAFTER, "VPN state changed but post-cmd exited "
                       "with non-zero: {}".format(retcode))


def get_profile(profile):
    """Using the provided Read the configuration file and get the connection parameters.
    """
    config = "Settings"
    params = {
        "host": None,       # Host to connect
        "group": None,      # Group used in connection profile
        "login": None,      # Username
        "password": None,
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
    conf.readfp(configdata)

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
    VPN = "/opt/cisco/anyconnect/bin/vpn"
    parser = argparse.ArgumentParser(
        description="Interact with Cisco's AnyConnect VPN client"
    )
    parser.add_argument("-c", "--cmd", default=VPN,
                        help="Command and path to launch the vpn binary (default: {})".format(VPN))
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Verbosity level. Warning on -vv (highest level) user input will be printed on screen")

    parser.add_argument("--version", action="store_true",
                        help="Print the version of panyc and the VPN client")

    subparser = parser.add_subparsers(dest="action")

    connect = subparser.add_parser("connect")
    connect.add_argument("profile",
                         help="Name of connection profile (check README) or '-' to read from stdin.")

    subparser.add_parser("disconnect")
    subparser.add_parser("status")

    args = parser.parse_args()

    if args.action is None and not args.version:
        raise parser.error("Argument: 'action' is required unless '--version' is given.")

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
