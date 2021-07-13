# Copyright (c) 2015
#
# All rights reserved.
#
# This file is distributed under the Clear BSD license.
# The full text can be found in LICENSE in the root directory.
"""Lsmod shows loaded kernel modules."""
import re

from boardfarm.tests import rootfs_boot


class KernelModules(rootfs_boot.RootFSBootTest):
    """Lsmod shows loaded kernel modules."""

    def runTest(self):
        """Run lsmod command and shows kernel modules."""
        board = self.dev.board

        board.check_output("lsmod | wc -l")
        tmp = re.search(r"\d+", board.before)
        num = int(tmp.group(0)) - 1  # subtract header line
        board.check_output("lsmod | sort")
        self.result_message = f"{num} kernel modules are loaded."
        self.logged["num_loaded"] = num
