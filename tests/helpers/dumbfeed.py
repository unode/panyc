#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import tty
import termios
import select
import time


class ExitError(Exception):
    pass


class Protocol(object):
    # Lines to ignore and treat as a comment
    COMMENT = b"#"
    READING = b"<"
    WRITING = b">"

    def __init__(self):
        self.chunk = []
        self.steps = []
        # reading or writing
        self.previous_step = None

    def feed(self, line):
        """Parsing the protocol file
        """
        if line.startswith(Protocol.READING):
            if self.previous_step is None:
                self.chunk_line(line)
                self.previous_step = Protocol.READING

            elif self.previous_step is Protocol.READING:
                self.chunk_line(line)

            elif self.previous_step is Protocol.WRITING:
                self.done()
                self.chunk_line(line)

            else:
                raise ExitError("Invalid previous step {0}".format(self.previous_step))

            self.previous_step = Protocol.READING

        elif line.startswith(Protocol.WRITING):
            if self.previous_step is None:
                self.chunk_line(line)
                self.previous_step = Protocol.WRITING

            elif self.previous_step is Protocol.WRITING:
                self.chunk_line(line)

            elif self.previous_step is Protocol.READING:
                self.done()
                self.chunk_line(line)

            else:
                raise ExitError("Invalid previous step {0}".format(self.previous_step))

            self.previous_step = Protocol.WRITING

        elif line.startswith(Protocol.COMMENT):
            pass

        else:
            raise ExitError("Invalid protocol specification. "
                            "Lines need to start with either {0}, {1} or {2}. "
                            "It starts with '{3}'"
                            .format(Protocol.READING, Protocol.WRITING,
                                    Protocol.COMMENT, line[:5]))

    def done(self):
        """Finish parsing each block
        """
        self.steps.append(
            (self.previous_step, b''.join(self.chunk).decode("utf8"))
        )
        self.chunk = []

    def chunk_line(self, line):
        self.chunk.append(line[1:])

    @staticmethod
    def write(char):
        sys.stdout.write(char)

        # Only flush at the end of each line
        if char == "\n":
            sys.stdout.flush()

    @staticmethod
    def _is_there_data():
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

    def read(self, timeout=5000, step=100):
        # convert miliseconds to fraction of second
        step = step / 1000.0
        timeout = timeout / 1000.0

        try:
            # Total waiting time
            wait_time = 0

            while wait_time <= timeout:
                start = time.time()

                if self._is_there_data():
                    c = sys.stdin.readline()
                    if c == '\x1b':         # x1b is ESC TODO (so what? what's the relevance)
                        return

                    return c

                time.sleep(step)
                wait_time += time.time() - start

            raise TimeoutError("Failed to receive a reply after {} miliseconds".format(timeout))

        finally:
            pass

    def run(self):
        for step, data in self.steps:
            for line in data.splitlines(True):
                if step == Protocol.WRITING:
                    self.write(line)

                elif step == Protocol.READING:
                    try:
                        read = self.read()
                    except TimeoutError:
                        raise ExitError("Expected data via stdin that never got "
                                        "delivered {0}".format(line))

                    if read != line:
                        raise ExitError("Unexpected data received via stdin: "
                                        "Expected {0!r} and got {1!r}".format(line, read))


def parse_protocol(file):
    proto = Protocol()

    with open(file, 'rb') as fh:
        for line in fh:
            proto.feed(line)

        proto.done()

    return proto


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage:", sys.argv[0], "filename_with_protocol.data")
        sys.exit(1)

    proto = parse_protocol(sys.argv[1])

    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    try:
        proto.run()
    except ExitError as e:
        sys.stderr.write("Exited with errors:\n")
        sys.stderr.write("{}\n".format(e))
        sys.exit(2)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

# vim: ai sts=4 et sw=4
