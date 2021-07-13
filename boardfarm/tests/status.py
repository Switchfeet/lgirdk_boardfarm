# Copyright (c) 2015
#
# All rights reserved.
#
# This file is distributed under the Clear BSD license.
# The full text can be found in LICENSE in the root directory.

import re

import pexpect

from boardfarm.devices import prompt
from boardfarm.tests import rootfs_boot


class Logread(rootfs_boot.RootFSBootTest):
    """Recorded syslog."""

    def runTest(self):
        """Executing Logread."""
        board = self.dev.board

        board.sendline("\nlogread")
        board.expect("logread")
        board.expect("OpenWrt", timeout=5)
        board.expect(prompt)


class DiskUse(rootfs_boot.RootFSBootTest):
    """Checked disk use."""

    def runTest(self):
        """Executing DiskUse."""
        board = self.dev.board

        board.sendline("\ndf -k")
        board.expect("Filesystem", timeout=5)
        board.expect(prompt)
        board.sendline("du -k | grep -v ^0 | sort -n | tail -20")
        board.expect(prompt)


class TopCheck(rootfs_boot.RootFSBootTest):
    """Ran "top" to see current processes."""

    def runTest(self):
        """Executing current processes."""
        board = self.dev.board

        board.sendline("\ntop -b -n 1")
        board.expect(pexpect.TIMEOUT, timeout=2)
        try:
            board.expect(prompt, timeout=2)
        except Exception:
            # some versions of top do not support '-n'
            # must CTRL-C to kill top
            board.sendcontrol("c")


class UciShow(rootfs_boot.RootFSBootTest):
    """Dumped all current uci settings."""

    def runTest(self):
        """Executing uci setting."""
        board = self.dev.board

        board.sendline("\nls -l /etc/config/")
        board.expect("/etc/config/", timeout=5)
        board.expect(prompt)
        board.sendline("ls -l /etc/config/ | wc -l")
        board.expect(r"(\d+)\r\n")
        num_files = int(board.match.group(1))
        board.expect(prompt)
        board.sendline("uci show")
        board.expect(prompt, searchwindowsize=50)
        self.result_message = (
            f"Dumped all current uci settings from {num_files} files in /etc/config/."
        )


class DhcpLeaseCheck(rootfs_boot.RootFSBootTest):
    """Checked dhcp.leases file."""

    def runTest(self):
        """Executing dhcp lease."""
        board = self.dev.board

        board.sendline("\ncat /tmp/dhcp.leases")
        board.expect("leases")
        board.expect(prompt)


class IfconfigCheck(rootfs_boot.RootFSBootTest):
    """Ran 'ifconfig' to check interfaces."""

    def runTest(self):
        """Executing ifconfig check prompt."""
        board = self.dev.board

        board.sendline("\nifconfig")
        board.expect("ifconfig")
        board.expect(prompt)
        results = re.findall(
            r"([A-Za-z0-9-\.]+)\s+Link.*\n.*addr:([^ ]+)", board.before
        )
        tmp = ", ".join([f"{x} {y}" for x, y in results])
        board.sendline("route -n")
        board.expect(prompt)
        self.result_message = f"ifconfig shows ip addresses: {tmp}"


class MemoryUse(rootfs_boot.RootFSBootTest):
    """Checked memory use."""

    def runTest(self):
        """Executing memory use cmd."""
        board = self.dev.board

        board.sendline("\nsync; echo 3 > /proc/sys/vm/drop_caches")
        board.expect("echo 3")
        board.expect(prompt, timeout=5)
        # There appears to be a tiny, tiny chance that
        # /proc/meminfo won't exist, so try one more time.
        for _ in range(2):
            try:
                board.sendline("cat /proc/meminfo")
                board.expect(r"MemTotal:\s+(\d+) kB", timeout=5)
                break
            except Exception:
                pass
        mem_total = int(board.match.group(1))
        board.expect(r"MemFree:\s+(\d+) kB")
        mem_free = int(board.match.group(1))
        board.expect(prompt)
        mem_used = mem_total - mem_free
        self.result_message = "Used memory: %s MB. Free memory: %s MB." % (
            mem_used / 1000,
            mem_free / 1000,
        )
        self.logged["mem_used"] = mem_used / 1000


class SleepHalfMinute(rootfs_boot.RootFSBootTest):
    """Slept 30 seconds."""

    def recover(self):
        """Recover to initial prompt."""
        board = self.dev.board

        board.sendcontrol("c")

    def runTest(self):
        """Executing board sleep to half minutes."""
        board = self.dev.board

        board.check_output("date")
        board.check_output("sleep 30", timeout=40)
        board.check_output("date")


class Sleep1Minute(rootfs_boot.RootFSBootTest):
    """Slept 1 minute."""

    def recover(self):
        """Recover to initial prompt."""
        board = self.dev.board

        board.sendcontrol("c")

    def runTest(self):
        """Executing board sleep to 1 minute."""
        board = self.dev.board

        board.check_output("date")
        board.check_output("sleep 60", timeout=70)
        board.check_output("date")


class Sleep2Minutes(rootfs_boot.RootFSBootTest):
    """Slept 2 minutes."""

    def recover(self):
        """Recover to initial prompt."""
        board = self.dev.board

        board.sendcontrol("c")

    def runTest(self):
        """Executing board sleep to 2 minute."""
        board = self.dev.board

        # Connections time out after 2 minutes, so this is useful to have.
        board.sendline("\n date")
        board.expect("date")
        board.expect(prompt)
        board.sendline("sleep 120")
        board.expect("sleep ")
        board.expect(prompt, timeout=130)
        board.sendline("date")
        board.expect("date")
        board.expect(prompt)


class Sleep5Minutes(rootfs_boot.RootFSBootTest):
    """Slept 5 minutes."""

    def recover(self):
        """Recover to initial prompt."""
        board = self.dev.board

        board.sendcontrol("c")

    def runTest(self):
        """Executing board sleep to 5 minute."""
        board = self.dev.board

        board.sendline("\n date")
        board.expect("date")
        board.expect(prompt)
        board.sendline("sleep 300")
        board.expect("sleep ")
        board.expect(prompt, timeout=310)
        board.sendline("date")
        board.expect("date")
        board.expect(prompt)
