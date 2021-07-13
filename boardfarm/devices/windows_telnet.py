#!/usr/bin/env python3
import ipaddress
import re
import sys

from boardfarm.lib.regexlib import AllValidIpv6AddressesRegex, WindowsMacFormat

from . import base, connection_decider


class WindowsTelnet(base.BaseDevice):
    """Class to connect and verify windows telnet."""

    model = "windows-telnet"
    # This prompt regex could use more work
    prompt = ["[a-zA-Z]:\\\\.*>$"]

    def __init__(self, *args, **kwargs):
        """Login the host connected to board using their credentials."""
        self.args = args
        self.kwargs = kwargs

        self.ip = self.kwargs["ipaddr"]
        self.username = self.kwargs.get("username", "Administrator")
        self.password = self.kwargs.get("password", "bigfoot1")

        conn_cmd = f"telnet {self.ip}"

        self.connection = connection_decider.connection(
            "local_cmd", device=self, conn_cmd=conn_cmd
        )
        self.connection.connect()
        self.linesep = "\r"

        self.expect("login: ")
        self.sendline(self.username)
        self.expect("password: ")
        self.sendline(self.password)
        self.expect(self.prompt)

        # Hide login prints, resume after that's done
        self.logfile_read = sys.stdout

    def get_ip(self, wifi_interface):
        """Get wifi interface ip from windows client.

        :param wifi_interface : Interface of wifi client
        :type wifi_interface : string
        :return : Matched pattern or None
        :rtype : string or boolean
        """
        self.sendline("netsh interface ip show config " + wifi_interface)

        self.expect("(.+)>", timeout=30)
        Wifi_log = self.match.group(1)

        match = re.search(r"IP Address:\s+([\d.]+)", str(Wifi_log))
        if match:
            return match.group(1)
        else:
            return None

    def ping(
        self, ping_ip, source_ip=None, ping_count=4, ping_interface=None, wait_time=30
    ):
        """Check the ping is successful from the windows client.

        :param ping_ip : IP to check the ping
        :type ping_ip : string
        :param source_ip : source ip to check the ping, defaults to None
        :type source_ip : string(, optional)
        :param ping_count : count of the ping output to check the packets, defaults to 4
        :type ping_count : string(, optional)
        :param ping_interface : Interface of the ip to ping , Not mandatory
        :type ping_ip : boolean(, optional)
        :param wait_time : Waiting timeout to expect the pattern
        :type wait_time : integer(, optional)
        :return : If matched return True else False
        :rtype : string
        """
        if source_ip is None:
            self.sendline(f"ping -n {ping_count} {ping_ip}")
        else:
            self.sendline(f"ping -S {source_ip} -n {ping_count} {ping_ip}")

        self.expect("(.+)>", timeout=wait_time)
        Wifi_log = self.match.group(1)

        match = re.search(
            r"Reply from .+: bytes=.+ TTL=|Reply from .* time=.*", str(Wifi_log)
        )
        if match:
            return True
        else:
            return False

    def set_dhcp(self, wifi_interface):
        """Set the dhcp for the wifi interface in windows client.

        :param wifi_interface : Interface of wifi
        :type wifi_interface : string
        """
        self.sendline("netsh interface ip set address " + wifi_interface + " dhcp")
        self.expect(self.prompt)

    def set_static_ip(self, wifi_interface, fix_ip, fix_mark, fix_gateway):
        """Set the static ip for the wifi interface in windows client.

        :param wifi_interface : Interface of wifi
        :type wifi_interface : string
        :param fix_ip : ip to be set as static
        :type fix_ip : string
        :param fix_mask : subnet mask of the static fix ip
        :type fix_mask : string
        :param fix_gateway : gateway ip address
        :type fix_gateway :  string
        """
        self.sendline(
            "netsh interface ip set address "
            + wifi_interface
            + " static "
            + fix_ip
            + " "
            + fix_mark
            + " "
            + fix_gateway
            + " 1"
        )
        self.expect(self.prompt)

    def get_default_gateway(self, wifi_interface):
        """Get the default gateway using wifi interface in windows client.

        :param wifi_interface : Interface of wifi
        :type wifi_interface : string
        :return : Matched pattern or None
        :rtype : string or boolean
        """
        self.sendline("netsh interface ip show config " + wifi_interface)

        self.expect("(.+)>", timeout=30)
        Wifi_log = self.match.group(1)

        match = re.search(r"Default Gateway:\s+([\d.]+)", str(Wifi_log))
        if match:
            return match.group(1)
        else:
            return None

    def get_interface_ipaddr(self, interface):
        """Get the ipv4 address in windows client using interface.

        :param interface : Interface of wifi
        :type interface : string
        :raises assertion : Assert if ip address not found
        :return : ipv4 address or False
        :rtype : string or boolean
        """
        ip = self.get_ip(interface)

        if ip is not None:
            return ip
        else:
            raise AssertionError("Can't get interface ip")

    def get_interface_ip6addr(self, interface):
        """Get the ipv6 address in windows client using interface.

        :param interface : Interface of wifi
        :type interface : string
        :return : ipv6 address
        :rtype : string
        """
        self.sendline(f"netsh interface ipv6 show addresses {interface}")
        self.expect(self.prompt)
        for match in re.findall(AllValidIpv6AddressesRegex, self.before):
            ipv6addr = ipaddress.IPv6Address(str(match))
            if not ipv6addr.is_link_local:
                return ipv6addr

    def get_interface_macaddr(self, interface):
        """Get the mac address in windows client using interface.

        :param interface : Interface of wifi
        :type interface : string
        :param /NH : Specifies that the "Column Header" should not be displayed in the output.
        Valid only for TABLE and CSV formats. Not mandatory
        :param /V  : Specifies that verbose output is displayed. Not mandatory
        :return : mac address
        :rtype : string
        """
        self.sendline("getmac /V /NH")
        self.expect(f"{interface!s}.*({WindowsMacFormat!s}).*\r\n")
        macaddr = self.match.group(1).replace("-", ":")
        self.expect(self.prompt)
        return macaddr
