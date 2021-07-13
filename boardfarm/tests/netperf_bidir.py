# Copyright (c) 2015
#
# All rights reserved.
#
# This file is distributed under the Clear BSD license.
# The full text can be found in LICENSE in the root directory.

from boardfarm import lib
from boardfarm.tests import netperf_reverse_test


class NetperfBidirTest(netperf_reverse_test.NetperfReverseTest):
    def runTest(self):
        board = self.dev.board
        lan = self.dev.lan

        board.sendline("mpstat -P ALL 30 1")
        opts = ""
        num_conns = 1

        up = down = 0.0
        for _ in range(0, num_conns):
            self.run_netperf_cmd(lan, f"192.168.0.1 -c -C -l 30 -- {opts}")
            self.run_netperf_cmd(
                lan, f"192.168.0.1 -c -C -l 30 -t TCP_MAERTS -- {opts}"
            )

        for _ in range(0, num_conns):
            up += float(self.run_netperf_parse(lan))
            down += float(self.run_netperf_parse(lan))

        board.expect(r"Average.*idle\r\nAverage:\s+all(\s+[0-9]+.[0-9]+){10}\r\n")
        idle_cpu = float(board.match.group(1))
        avg_cpu = 100 - float(idle_cpu)

        msg = f"Bidir speed was {up + down} 10^6Mbits/sec with {avg_cpu} average cpu"
        lib.common.test_msg(msg)
        self.result_message = msg
