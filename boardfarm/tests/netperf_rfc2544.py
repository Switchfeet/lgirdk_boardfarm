"""Single test to simulate RFC2544."""
# Copyright (c) 2015
#
# All rights reserved.
#
# This file is distributed under the Clear BSD license.
# The full text can be found in LICENSE in the root directory.

from boardfarm.devices import prompt
from boardfarm.tests import rootfs_boot


class NetperfRFC2544(rootfs_boot.RootFSBootTest):
    """Single test to simulate RFC2544."""

    def runTest(self):
        """Single test to simulate RFC2544."""
        board = self.dev.board
        lan = self.dev.lan

        for sz in ["74", "128", "256", "512", "1024", "1280", "1518"]:
            print(f"running {sz} UDP test")
            lan.sendline(f"netperf -H 192.168.0.1 -t UDP_STREAM -l 60 -- -m {sz}")
            lan.expect_exact(f"netperf -H 192.168.0.1 -t UDP_STREAM -l 60 -- -m {sz}")
            lan.expect("UDP UNIDIRECTIONAL")
            lan.expect(prompt, timeout=90)
            board.sendline()
            board.expect(prompt)
