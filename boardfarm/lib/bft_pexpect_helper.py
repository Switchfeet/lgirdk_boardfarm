"""Class functions to help boardfarm with pexpect logging."""
import getpass
import inspect
import os
import sys
import time

import pexpect
import termcolor

from boardfarm.lib.bft_logging import o_helper
from boardfarm.tests_wrappers import throw_pexpect_error

IS_PYTHON_3 = sys.version_info > (3, 0)

BFT_DEBUG = "BFT_DEBUG" in os.environ


def print_bold(msg):
    """Print bold."""
    termcolor.cprint(msg, None, attrs=["bold"])


def frame_index_out_of_file(this_file=__file__):
    """
    Look for the last function called before calling something from this file.

    For example:
    - foo1()
    - foo2()
    - dev.sendline()
    - wrapper()
    - dev.send()

    It would return foo2 and the line number that it was called from
    """
    frame_count = len(inspect.stack())

    for index in range(frame_count):
        frame = inspect.stack()[index][0]
        info = inspect.getframeinfo(frame)
        if info.filename != this_file:

            keep_going = False
            for remaining in range(index + 1, frame_count):
                next_frame = inspect.stack()[remaining][0]
                next_info = inspect.getframeinfo(next_frame)
                if next_info.filename == this_file:
                    keep_going = True
                    break

            if keep_going:
                continue

            return index

    raise Exception("This should never hit")


def caller_file_line(i):
    """Print a simple debug line.

    In a given frame index for the file, function, and line number
    """
    caller = inspect.stack()[i]  # caller of spawn or pexpect
    frame = caller[0]
    info = inspect.getframeinfo(frame)

    return "%s: %s(): line %s" % (info.filename, info.function, info.lineno)


# global sudo password
password = None


class bft_pexpect_helper(pexpect.spawn):
    """Boardfarm helper for logging pexpect and making minor tweaks."""

    def __setattr__(self, key, value):
        """Every time when an attribute assignment is attempted, the function is called."""
        # pexpect name start with <.*>
        # idea is to check for all names before letting pexpect set the name
        if key == "name":
            # check for static name variable
            name = getattr(type(self), "name", None)
            if name:
                if value[0] == "<":
                    # the code reached pexpect to set name
                    # keep the class static variable name
                    value = name
            else:
                # if static name not in class
                # if a different name is already set apart from pexpect one
                # use that name, since a kwarg in child init must have set the name
                name = getattr(self, "name", None)
                if name and name[0] != "<":
                    value = name
        super(bft_pexpect_helper, self).__setattr__(key, value)

    class spawn(pexpect.spawn):
        """spwan pexpect session with password if sudo."""

        def __init__(self, *args, **kwargs):
            """Instance Initialization."""
            if IS_PYTHON_3:
                kwargs["encoding"] = "latin1"
            pexpect.spawn.__init__(self, *args, **kwargs)

            global password
            if (
                (len(args) > 0 and "sudo" in args[0])
                or "sudo" in kwargs.get("command", "")
                or True in ["sudo" in x for x in kwargs.get("args", [])]
            ):
                print_bold("NOTE: sudo helper running")
                if (
                    self.expect(
                        [
                            r"\[sudo\] password for [^:]*: ",
                            pexpect.TIMEOUT,
                            pexpect.EOF,
                        ],
                        timeout=5,
                    )
                    != 0
                ):
                    return
                if password is None:
                    password = getpass.getpass(self.match.group(0))

                self.sendline(password)

    def __init__(self, *args, **kwargs):
        """Instance initialization."""
        # Filters out boardfarm specific
        # Bad args that pexpext does not take, higher classes should have popped
        # them off, but we catch them all here in case
        bad_args = [
            "tftp_username",
            "connection_type",
            "power_password",
            "rootfs",
            "kernel",
            "power_outlet",
            "web_proxy",
            "tftp_port",
            "ssh_password",
            "tftp_server",
            "config",
            "power_ip",
            "conn_cmd",
            "power_username",
            "start",
            "tftp_password",
        ]
        for arg in bad_args:
            kwargs.pop(arg, None)
        if IS_PYTHON_3:
            kwargs["encoding"] = "latin1"
        super(bft_pexpect_helper, self).__init__(*args, **kwargs)

    def get_logfile_read(self):
        """Get log file read."""
        if hasattr(self, "_logfile_read"):
            return self._logfile_read
        else:
            return None

    def set_logfile_read(self, value):
        """Set log file read."""
        if value is None:
            self._logfile_read = None
            return

        if isinstance(value, o_helper):
            self._logfile_read = value
        elif value is not None:
            self._logfile_read = o_helper(self, value, getattr(self, "color", None))

    logfile_read = property(get_logfile_read, set_logfile_read)

    def expect_prompt(self, timeout=30):
        """Expect prompt."""
        self.expect(self.prompt, timeout=timeout)

    def check_output(self, cmd, timeout=30):
        """Send a string to device then  return the output between that string and the next prompt."""
        self.sendline("\n" + cmd)
        self.expect_exact(cmd, timeout=5)
        try:
            self.expect(self.prompt, timeout=timeout)
        except Exception:
            self.sendcontrol("c")
            raise Exception(
                "Command did not complete within %s seconds. %s prompt was not seen."
                % (timeout, self.name)
            )
        return self.before.strip()

    def write(self, string):
        """Log file write."""
        self._logfile_read.write(string)

    def interact(self, escape_character=None, input_filter=None, output_filter=None):
        """Provide with current session."""
        if escape_character is None:
            escape_character = chr(29)

        o = self._logfile_read
        self.logfile_read = None
        ret = super(bft_pexpect_helper, self).interact(
            escape_character, input_filter, output_filter
        )
        self.logfile_read = o

        return ret

    # this is here for the debug parser to egress this file only
    # when printing calling stacks
    def sendline(self, s=""):
        """Send input command to the active pexpect session."""
        if BFT_DEBUG and self.getecho():
            idx = frame_index_out_of_file()
            print_bold("%s = sending: %s" % (caller_file_line(idx), repr(s)))

        return super(bft_pexpect_helper, self).sendline(s)

    def send(self, s):
        """Send input command char by char to the active pexpect session."""
        if BFT_DEBUG and self.getecho():
            idx = frame_index_out_of_file()
            print_bold("%s = sending: %s" % (caller_file_line(idx), repr(s)))

        if self.delaybetweenchar is not None:
            ret = 0
            for char in s:
                ret += super(bft_pexpect_helper, self).send(char)
                time.sleep(self.delaybetweenchar)
            return ret

        return super(bft_pexpect_helper, self).send(s)

    @throw_pexpect_error
    def expect_helper(self, pattern, wrapper, *args, **kwargs):
        """Check for expected pattern and raise exception."""
        if not BFT_DEBUG:
            return wrapper(pattern, *args, **kwargs)

        idx = frame_index_out_of_file()
        print_bold("%s = expecting: %s" % (caller_file_line(idx), repr(pattern)))
        try:
            ret = wrapper(pattern, *args, **kwargs)

            frame = caller_file_line(idx)

            if hasattr(self.match, "group"):
                print_bold("%s = matched: %s" % (frame, repr(self.match.group())))
            else:
                print_bold("%s = matched: %s" % (frame, repr(pattern)))
            return ret
        except Exception:
            print_bold("expired")
            raise

    def expect(self, pattern, *args, **kwargs):
        """Call expect helper function wrapping bft_pexpect_helper."""
        wrapper = super(bft_pexpect_helper, self).expect

        return self.expect_helper(pattern, wrapper, *args, **kwargs)

    def expect_exact(self, pattern, *args, **kwargs):
        """Call expect helper function wrapping bft_pexpect_helper."""
        wrapper = super(bft_pexpect_helper, self).expect_exact

        return self.expect_helper(pattern, wrapper, *args, **kwargs)

    def sendcontrol(self, char):
        """Send control char to pexecpt session."""
        if BFT_DEBUG:
            print_bold(
                "%s = sending: control-%s"
                % (caller_file_line(frame_index_out_of_file()), repr(char))
            )

        return super(bft_pexpect_helper, self).sendcontrol(char)


def spawn_ssh_pexpect(
    ip,
    user="root",
    pw="bigfoot1",
    prompt=None,
    port="22",
    via=None,
    color=None,
    o=sys.stdout,
    extra_args="",
):
    """Provide a quick way to spawn an ssh session.

    (this avoids having to import the SshConnection class from devices)
    Uses hardcoded options: -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null

    :param ip: ip address to ssh to
    :type ip: string
    :param user: username used by ssh (default 'root')
    :type user: string
    :param pw: password (default 'bigfoot1')
    :type pw: string
    :param prompt: expected prompt (default None, which creates one on the fly using the username in the "%s@.*$" pattern)
    :type prompt: string
    :param port: ssh port (default "22")
    :type port: string
    :param via: can be used to pass another pexpect session (default None, i.e. will ssh from localhost)
    :type via: string
    :param color: fonts output color (default None)
    :type color: string
    :param o: ssh output stream (default sys.stdout)
    :type o: string
    :param extra_args: additional arguments APPENDED to the ssh command line (default "")
        E.g.: for a socks5 tunnnel with port 50000: extra_args="-D 50000 -N -v -v"
    :type extra_args: string
    """
    if via:
        p = via.sendline(
            "ssh %s@%s -p %s -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null %s"
            % (user, ip, port, extra_args)
        )
        p = via
    else:
        p = bft_pexpect_helper.spawn(
            "ssh %s@%s -p %s -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null %s"
            % (user, ip, port, extra_args)
        )

    i = p.expect(["yes/no", "assword:", "Last login"], timeout=30)
    if i == 0:
        p.sendline("yes")
        i = p.expect(["Last login", "assword:"])
    if i == 1:
        p.sendline(pw)
    else:
        pass

    if prompt is None:
        p.prompt = "%s@.*$" % user
    else:
        p.prompt = prompt

    p.expect(p.prompt)

    from termcolor import colored

    class o_helper_foo:
        def __init__(self, color):
            self.color = color

        def write(self, string):
            o.write(colored(string, color))

        def flush(self):
            o.flush()

    if color is not None:
        p.logfile_read = o_helper_foo(color)
    else:
        p.logfile_read = o

    return p
