"""This file holds functions related to ipv4, ipv6 and mac addresses."""
import ipaddress
import re

import netaddr
import pexpect

from boardfarm.exceptions import BftIfaceNoIpV4Addr, BftIfaceNoIpV6Addr
from boardfarm.lib.regexlib import (
    InterfaceIPv4_AddressRegex,
    InterfaceIPv6_AddressRegex,
    LinuxMacFormat,
    NetmaskIPv4_AddressRegex,
)


class bft_iface:
    """Holds functions related to ipv4, ipv6 and mac addresses."""

    _ipv4 = None
    _ipv6 = None
    _ipv6_link_local = None
    _mac = None

    def __str__(self):
        """Given the device name, returns as string."""
        return str(self.dev.name)

    def __init__(self, device, iface, ip_cmd="ifconfig"):
        """Instance initialisation."""
        self.dev = device
        self.iface = iface
        self.ip_cmd = ip_cmd

    def refresh(self):
        """Single function to get the ipv4, ipv6 and mac address."""
        output = self.dev.check_output(f"{self.ip_cmd} {self.iface}")
        try:
            self.get_interface_ipv4addr(output)
        except BftIfaceNoIpV4Addr:
            pass

        try:
            self.get_interface_ipv6addr(output)
        except BftIfaceNoIpV6Addr:
            pass

        self.get_interface_macaddr()

    def get_interface_ipv4addr(self, output=None):
        """
        Get the ipv4 interface address.

        This will return the object of ipv4 interface module.

        """
        if output is None:
            output = self.dev.check_output(f"{self.ip_cmd} {self.iface}")

        ipaddr = re.search(InterfaceIPv4_AddressRegex, output)
        if ipaddr:
            ipaddr4 = re.search(InterfaceIPv4_AddressRegex, output).group(1)
            if re.search(NetmaskIPv4_AddressRegex, output):
                netmask = re.search(NetmaskIPv4_AddressRegex, output).group(1)
                ipaddr4 = "/".join([ipaddr4, netmask])
            try:
                self._ipv4 = ipaddress.IPv4Interface(str(ipaddr4))
            except ipaddress.AddressValueError:
                pass

        if self._ipv4 is None:
            raise BftIfaceNoIpV4Addr

    def get_interface_ipv6addr(self, output=None):
        """
        Get the ipv6 interface address.

        This will return the object of ipv6 interface module.
        """
        if output is None:
            output = self.dev.check_output(f"{self.ip_cmd} {self.iface}")

        ip_list = re.findall(InterfaceIPv6_AddressRegex, output)
        for ip in ip_list:
            try:
                if ip.startswith("fe80"):
                    self._ipv6_link_local = ipaddress.IPv6Interface(str(ip))
                else:
                    self._ipv6 = ipaddress.IPv6Interface(str(ip))
            except ipaddress.AddressValueError:
                pass

        if self._ipv6 is None:
            raise BftIfaceNoIpV6Addr

    def get_interface_macaddr(self):
        """
        Get the interface mac address.

        This will return the object of mac interface module.

        """
        self.dev.sendline(f"cat /sys/class/net/{self.iface}/address")
        self.dev.expect_exact(f"cat /sys/class/net/{self.iface}/address")
        self.dev.expect(LinuxMacFormat)
        self._mac = netaddr.EUI(self.dev.after)
        self.dev.expect(pexpect.TIMEOUT, timeout=1)

    @property
    def ipv4(self):
        """Get interface ipv4 address."""
        if not getattr(self, "_ipv4", None):
            self.get_interface_ipv4addr()

        return self._ipv4.ip

    @property
    def netmask(self):
        """Get interface ipv4 netmask."""
        if not getattr(self, "_ipv4", None):
            self.get_interface_ipv4addr()

        return self._ipv4.netmask

    @property
    def network(self):
        """Get interface ipv4 network address."""
        if not getattr(self, "_ipv4", None):
            self.get_interface_ipv4addr()

        return self._ipv4.network

    @property
    def ipv6(self):
        """Get interface ipv6 address."""
        if not getattr(self, "_ipv6", None):
            self.get_interface_ipv6addr()

        return self._ipv6.ip

    @property
    def network_v6(self):
        """Get interface ipv6 network address."""
        if not getattr(self, "_ipv6", None):
            self.get_interface_ipv6addr()

        return self._ipv6.network

    @property
    def prefixlen(self):
        """Get interface ipv6 prefix length."""
        if not getattr(self, "_ipv6", None):
            self.get_interface_ipv6addr()

        return self._ipv6._prefixlen

    @property
    def ipv6_link_local(self):
        """Get interface ipv6 address."""
        if not getattr(self, "_ipv6_link_local", None):
            self.get_interface_ipv6addr()

        return self._ipv6_link_local.ip

    @property
    def mac_address(self):
        """Get interface mac address."""
        if not getattr(self, "_mac", None):
            self.get_interface_macaddr()

        return self._mac


if __name__ == "__main__":
    import sys

    from boardfarm.devices.base import BaseDevice

    class DummyDevice(BaseDevice):
        """Dummy Device."""

        def __init__(self):
            """Instance initialisation."""
            super().__init__(command="bash --noprofile --norc", encoding="utf-8")
            self.sendline('export PS1="dummy>"')
            self.expect_exact('export PS1="dummy>"')
            self.prompt = ["dummy>"]

    dev = DummyDevice()
    dev.obj = bft_iface(dev, sys.argv[1], sys.argv[2])
    dev.obj.refresh()
