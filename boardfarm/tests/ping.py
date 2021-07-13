"""Ping functions between North and south bound devices of DUT."""
# Copyright (c) 2015
#
# All rights reserved.
#
# This file is distributed under the Clear BSD license.
# The full text can be found in LICENSE in the root directory.

from boardfarm import lib
from boardfarm.tests import rootfs_boot


class RouterPingWanDev(rootfs_boot.RootFSBootTest):
    """Router can ping device through WAN interface."""

    def test_main(self):
        """Perform Ping action."""
        board = self.dev.board
        wan = self.dev.wan
        if not wan:
            msg = "No WAN Device defined, skipping ping WAN test."
            lib.common.test_msg(msg)
            self.skipTest(msg)
        board.sendline(f"\nping -c5 {wan.gw}")
        board.expect("5 (packets )?received", timeout=15)
        board.expect(board.prompt)

    def recover(self):
        """Exit Ping action."""
        self.dev.board.sendcontrol("c")


class RouterPingInternet(rootfs_boot.RootFSBootTest):
    """Router can ping internet address by IP."""

    def test_main(self):
        """Perform Ping action."""
        board = self.dev.board
        board.sendline("\nping -c2 8.8.8.8")
        board.expect("2 (packets )?received", timeout=15)
        board.expect(board.prompt)


class RouterPingInternetName(rootfs_boot.RootFSBootTest):
    """Router can ping internet address by name."""

    def test_main(self):
        """Perform Ping action."""
        board = self.dev.board
        board.sendline("\nping -c2 www.google.com")
        board.expect("2 (packets )?received", timeout=15)
        board.expect(board.prompt)


class LanDevPingRouter(rootfs_boot.RootFSBootTest):
    """Device on LAN can ping router."""

    def test_main(self):
        """Perform Ping action."""
        board = self.dev.board
        lan = self.dev.lan
        if not lan:
            msg = "No LAN Device defined, skipping ping test from LAN."
            lib.common.test_msg(msg)
            self.skipTest(msg)
        router_ip = board.get_interface_ipaddr(board.lan_iface)
        lan.sendline(f"\nping -i 0.2 -c 5 {router_ip}")
        lan.expect("PING ")
        lan.expect("5 (packets )?received", timeout=15)
        lan.expect(lan.prompt)


class LanDevPingWanDev(rootfs_boot.RootFSBootTest):
    """Device on LAN can ping through router."""

    def test_main(self):
        """Perform Ping action."""
        lan = self.dev.lan
        wan = self.dev.wan
        if not lan:
            msg = "No LAN Device defined, skipping ping test from LAN."
            lib.common.test_msg(msg)
            self.skipTest(msg)
        if not wan:
            msg = "No WAN Device defined, skipping ping WAN test."
            lib.common.test_msg(msg)
            self.skipTest(msg)
        lan.sendline(f"\nping -i 0.2 -c 5 {wan.gw}")
        lan.expect("PING ")
        lan.expect("5 (packets )?received", timeout=15)
        lan.expect(lan.prompt)

    def recover(self):
        """Exit Ping action."""
        self.dev.lan.sendcontrol("c")


class LanDevPingInternet(rootfs_boot.RootFSBootTest):
    """Device on LAN can ping through router to internet."""

    def test_main(self):
        """Perform Ping action."""
        lan = self.dev.lan
        if not lan:
            msg = "No LAN Device defined, skipping ping test from LAN."
            lib.common.test_msg(msg)
            self.skipTest(msg)
        lan.sendline("\nping -c2 8.8.8.8")
        lan.expect("2 (packets )?received", timeout=10)
        lan.expect(lan.prompt)

    def recover(self):
        """Exit Ping action."""
        self.dev.lan.sendcontrol("c")
