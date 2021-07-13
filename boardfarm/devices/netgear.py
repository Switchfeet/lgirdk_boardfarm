# !/usr/bin/env python
# Copyright (c) 2015
#
# All rights reserved.
#
# This file is distributed under the Clear BSD license.
# The full text can be found in LICENSE in the root directory.

import logging
import sys

from boardfarm.lib.bft_pexpect_helper import bft_pexpect_helper

from . import linux

# Netgear Switch Prompt
prompt = r"\(M4100-50G\) "
logger = logging.getLogger("bft")


class NetgearM4100(linux.LinuxDevice):
    """A netgear switch allows for changing connections by \
    modifying VLANs on ports extends LinuxDevice."""

    def __init__(self, conn_cmd, username="admin", password="bigfoot1"):
        """Initialize variables in NetgearM4100.

        :param self: self object
        :type self: object
        :param conn_cmd: conn_cmd to connect to device
        :type conn_cmd: string
        :param username: username to be for connection, defaults to "admin"
        :type username: string
        :param password: password to connect to device, defaults to "bigfoot1"
        :type password: string
        """
        bft_pexpect_helper.spawn.__init__(self, "/bin/bash", args=["-c", conn_cmd])
        self.logfile_read = sys.stdout
        self.username = username
        self.password = password
        self.prompt = prompt
        self.connect()

    def connect(self):
        """Connect to the device.

        :param self: self object
        :type self: object
        """
        self.sendline("\n")
        i = self.expect(["User:", prompt], timeout=20)
        if i == 0:
            self.sendline(self.username)
            self.expect("Password:")
            self.sendline(self.password)
            self.expect(prompt)

    def disconnect(self):
        """Disconnect to the device.

        :param self: self object
        :type self: object
        """
        # Leave config mode
        self.sendline("exit")
        self.expect(prompt)
        # Leave privileged mode
        self.sendline("exit")
        self.expect(prompt)
        # Quit
        self.sendline("quit")
        self.expect("User:")
        self.close()

    def change_port_vlan(self, port, vlan):
        """Change the vlan associated to a port.

        :param self: self object
        :type self: object
        :param port: port for which vlan to be changed
        :type port: int
        :param vlan: vlan to be associated to the port
        :type vlan: string
        """
        # Enter privileged mode
        self.sendline("enable")
        i = self.expect([prompt, "Password:"])
        if i == 1:
            self.sendline(self.password)
            self.expect(prompt)
        # Enter config mode
        self.sendline("configure")
        self.expect(prompt)
        # Enter interface config mode
        port_name = "0/%01d" % port
        self.sendline(f"interface {port_name}")
        self.expect(prompt)
        # Remove previous VLAN
        self.sendline("no vlan pvid")
        self.expect(prompt)
        self.sendline("vlan participation exclude 3-1024")
        self.expect(prompt)
        # Include new VLAN
        self.sendline(f"vlan pvid {vlan}")
        self.expect(prompt)
        self.sendline(f"vlan participation include {vlan}")
        self.expect(prompt)
        # Leave interface config mode
        self.sendline("exit")
        self.expect(prompt)

    def setup_standard_vlans(self, min_port=1, max_port=49):
        """Set up the standard vlans.

        Create enough VLANs, then put ports on VLANS such that:
        port 1 & 2 are on VLAN 3
        port 3 & 4 are on VLAN 4
        etc...
        Also remove all ports from VLAN 1 (default setting).


        :param self: self object
        :type self: object
        :param min_port: the start port to be associated
        :type min_port: int
        :param max_port: the end port to be assocauted
        :type max_port: int
        """
        # Enter privileged mode
        self.sendline("enable")
        i = self.expect([prompt, "Password:"])
        if i == 1:
            self.sendline("password")
            self.expect(prompt)
        # Create all VLANS
        self.sendline("vlan database")
        self.expect(prompt)
        self.sendline("vlan 3-50")
        self.expect(prompt)
        self.sendline("exit")
        self.expect(prompt)
        # Enter config mode
        self.sendline("configure")
        self.expect(prompt)
        # Remove all interfaces from VLAN 1 (default setting)
        self.sendline("interface 0/1-0/48")
        self.expect(prompt)
        self.sendline("vlan participation exclude 1")
        self.expect(prompt)
        self.sendline("exit")
        self.expect(prompt)
        # Loop over all interfaces
        pvid = 3  # initial offset of 3 due to netgear BS
        for i in range(min_port, max_port, 2):
            low = i
            high = i + 1
            # configure interfaces
            self.sendline("interface 0/%01d-0/%01d" % (low, high))
            self.expect(prompt)
            self.sendline(f"vlan pvid {pvid}")
            self.expect(prompt)
            self.sendline(f"vlan participation include {pvid}")
            self.expect(prompt)
            # Leave interface configuration
            self.sendline("exit")
            self.expect(prompt)
            pvid += 1

    def print_vlans(self):
        """Query each port on switch to see connected \
        mac addresses and Print connection table in the end.

        :param self: self object
        :type self: object
        """
        vlan_macs = {}
        # Enter privileged mode
        self.sendline("enable")
        i = self.expect([prompt, "Password:"])
        if i == 1:
            self.sendline("password")
            self.expect(prompt)
        # Check each port
        for p in range(1, 48):
            port_name = "0/%01d" % p
            self.sendline(f"show mac-addr-table interface {port_name}")
            tmp = self.expect(["--More--", prompt])
            if tmp == 0:
                self.sendline()
            result = self.before.split("\n")
            for line in result:
                if ":" in line:
                    mac, vlan, _ = line.split()
                    vlan = int(vlan)
                    if vlan not in vlan_macs:
                        vlan_macs[vlan] = []
                    vlan_macs[vlan].append(mac)
        logger.info("\n\n")
        logger.info("VLAN Devices")
        logger.info("---- -----------------")
        for vlan in sorted(vlan_macs):
            devices = [x for x in vlan_macs[vlan]]
            logger.info("%4s %s" % (vlan, " <-> ".join(devices)))


if __name__ == "__main__":
    switch = NetgearM4100(
        conn_cmd="telnet 10.0.0.64 6031", username="admin", password="password"
    )
    switch.print_vlans()
    switch.disconnect()
