# Copyright (c) 2018
#
# All rights reserved.
#
# This file is distributed under the Clear BSD license.
# The full text can be found in LICENSE in the root directory.
"""Captures traces for WAN and LAN devices."""
import pexpect

from boardfarm.tests import rootfs_boot


class TCPDumpWANandLAN(rootfs_boot.RootFSBootTest):
    """Captures traces for WAN and LAN devices."""

    opts = ""

    def runTest(self):
        """Run test to Capture traces for WAN and LAN devices."""
        board = self.dev.board
        wan = self.dev.wan
        lan = self.dev.lan

        for d in [wan, lan]:
            d.sendline(f"tcpdump -i {d.iface_dut} -w /tmp/tcpdump.pcap {self.opts}")

        board.expect(pexpect.TIMEOUT, timeout=15)

        for d in [wan, lan]:
            d.sendcontrol("c")

        # TODO: copy dumps to results/ dir for logging


class TCPDumpWANandLANfilterICMP(TCPDumpWANandLAN):
    """Captures ICMP traces for WAN and LAN devices."""

    opts = "icmp"
