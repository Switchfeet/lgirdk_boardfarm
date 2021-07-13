# Copyright (c) 2017
#
# All rights reserved.
#
# This file is distributed under the Clear BSD license.
# The full text can be found in LICENSE in the root directory.

import atexit
import ipaddress
import os
import signal
import sys

import pexpect

from boardfarm.lib.bft_pexpect_helper import bft_pexpect_helper
from boardfarm.lib.common import cmd_exists

from . import openwrt_router


class Qemu(openwrt_router.OpenWrtRouter):
    """Emulated QEMU board inherit the OpenWrtRouter.

    This class handles the operations relating to booting, reset and setup of QEMU device.
    QEMU is used to perform few of the code validation without the use of the actual board but rather QEMU device.
    """

    model = "qemux86"

    wan_iface = "eth0"
    lan_iface = "brlan0"

    lan_network = ipaddress.IPv4Network("10.0.0.0/24")
    lan_gateway = ipaddress.IPv4Address("10.0.0.1")

    # allowed open ports (starting point, dns is on wan?)
    wan_open_ports = ["22", "53"]

    cleanup_files = []
    kvm = False

    def __init__(
        self,
        model,
        conn_cmd,
        power_ip,
        power_outlet,
        output=sys.stdout,
        password="bigfoot1",
        web_proxy=None,
        tftp_server=None,
        tftp_username=None,
        tftp_password=None,
        tftp_port=None,
        connection_type=None,
        power_username=None,
        power_password=None,
        rootfs=None,
        kernel=None,
        mgr=None,
        **kwargs,
    ):
        """Initialize the variables that are used across function which include the tftp_server, credential, power_ip, credentials etc..

        :param model: Model of the QEMU device.
        :type model: string
        :param conn_cmd: The connection command that is used to connect to QEMU device
        :type conn_cmd: string
        :param power_ip: IP Address of power unit to which this device is connected
        :type power_ip: string
        :param power_outlet: Outlet # this device is connected
        :type power_outlet: string
        :param output: Stores the system standard output, defaults to sys.stdout
        :type output: string
        :param password: The password used to connect to the device, defaults to "bigfoot1"
        :type password: string
        :param web_proxy: The web proxy to be used, defaults to None
        :type web_proxy: string
        :param tftp_server: The tftp_server ip address, defaults to None
        :type tftp_server: string
        :param tftp_username: The tftp server userame, defaults to None
        :type tftp_username: string
        :param tftp_password: The tftp server password to be used, defaults to None
        :type tftp_password: string
        :param tftp_port: The port number that can be used to connect to tftp, defaults to None
        :type tftp_port: string
        :param connection_type: The connection type to used to connect.
        :type connection_type: string
        :param power_username: The username to be used over power unit connection to the device, defaults to None
        :type power_username: string
        :param power_password: The password to be used over power unit connection to the device, defaults to None
        :type power_password: string
        :param rootfs: The complete url of the image to be loaded, defaults to None
        :type rootfs: string
        :param kernel: The kernel image path to be used to flash to the device, defaults to None
        :type kernel: string
        :param ``**kwargs``: Extra set of arguments to be used if any.
        :type ``**kwargs``: dict
        :raises: Exception "The QEMU device type requires specifying a rootfs"
        """
        self.consoles = [self]
        self.dev = mgr

        assert cmd_exists("qemu-system-i386")

        if rootfs is None:
            raise Exception("The QEMU device type requires specifying a rootfs")

        def temp_download(url):
            """Download the image to the temp folder over the QEMU device.

            :param url: URL where the file is location (URL path of the file to be downloaded), defaults to None
            :type url: string
            :returns: The filename of the downloaded file.
            :rtype: string
            """
            dl_console = bft_pexpect_helper.spawn("bash --noprofile --norc")
            dl_console.sendline('export PS1="prompt>>"')
            dl_console.expect_exact("prompt>>")
            dl_console.sendline("mktemp")
            dl_console.expect("/tmp/tmp.*")
            fname = dl_console.match.group(0).strip()
            dl_console.expect_exact("prompt>>")
            self.cleanup_files.append(fname)
            atexit.register(self.run_cleanup_cmd)
            dl_console.logfile_read = sys.stdout
            print(f"Temp downloaded file = {url}")
            dl_console.sendline(f"curl -n -L -k '{url}' > {fname}")
            dl_console.expect_exact("prompt>>", timeout=500)
            dl_console.logfile_read = None
            dl_console.sendline("exit")
            dl_console.expect(pexpect.EOF)
            return fname

        if rootfs.startswith("http://") or rootfs.startswith("https://"):
            rootfs = temp_download(rootfs)

        cmd = f"{conn_cmd} {rootfs}"

        if kernel is not None:
            if kernel.startswith("http://") or kernel.startswith("https://"):
                kernel = temp_download(kernel)
            cmd += f" -kernel {kernel} --append root=/dev/hda2"

        # check if we can run kvm
        kvm_chk = bft_pexpect_helper.spawn("sudo kvm-ok")
        if 0 != kvm_chk.expect(["KVM acceleration can be used", pexpect.EOF]):
            cmd = cmd.replace("--enable-kvm ", "")
            self.kvm = False

        # TODO: add script=no,downscript=no to taps

        try:
            bft_pexpect_helper.spawn.__init__(
                self, command="/bin/bash", args=["-c", cmd], env=self.dev.env
            )
            self.expect(pexpect.TIMEOUT, timeout=1)
        except pexpect.EOF:
            self.pid = None
            if (
                "failed to initialize KVM: Device or resource busy" in self.before
                or "failed to initialize KVM: Cannot allocate memory" in self.before
            ):
                cmd = cmd.replace("--enable-kvm ", "")
                self.kvm = False
                bft_pexpect_helper.spawn.__init__(
                    self, command="/bin/bash", args=["-c", cmd], env=self.dev.env
                )
            else:
                raise

        self.cmd = cmd
        if kernel is None:
            self.expect(["SYSLINUX", "GNU GRUB"])
        self.logfile_read = output

        atexit.register(self.kill_console_at_exit)

    def run_cleanup_cmd(self):
        """Remove set of files for the clean up."""
        for f in self.cleanup_files:
            if os.path.isfile(f):
                os.remove(f)

    def close(self, *args, **kwargs):
        """Exist from the console and closes the session."""
        self.kill_console_at_exit()
        return super(Qemu, self).close(*args, **kwargs)

    def kill_console_at_exit(self):
        """Close the console over exit.Exists pexpect."""
        try:
            self.sendcontrol("a")
            self.send("c")
            self.sendline("q")
            self.kill(signal.SIGKILL)
        except Exception:
            pass

    def wait_for_boot(self):
        """Wait for the prompt after the reboot."""
        pass

    def setup_uboot_network(self, tftp_server=None):
        """Perform a uboot of the device over the network.

        :param tftp_server: Ip address of the TFTP server to be used for uboot, defaults to None
        :type tftp_server: string
        """
        pass

    def flash_rootfs(self, ROOTFS):
        """Flash the QEMU board with the ROOTFS (which in general is a patch update on the firmware).

        :param ROOTFS: Indicates the absolute location of the file to be used to flash.
        :type ROOTFS: string
        """
        pass

    def flash_linux(self, KERNEL):
        """Flash the QEMU board by copying file to the board using TFTP protocol.

        :param KERNEL: Indicates the absolute location of the file to be used to flash.
        :type KERNEL: string
        """
        pass

    def wait_for_linux(self):
        """Wait for the linux menu. Once the device is up will login and enter to root."""
        if self.kvm:
            tout = 60
        else:
            tout = 180

        for _ in range(0, tout, 10):
            self.sendline()
            i = self.expect([pexpect.TIMEOUT, "login:"] + self.prompt, timeout=10)
            if i == 1:
                self.sendline("root")
                self.expect(self.prompt, timeout=tout)
            if i >= 1:
                break

    def boot_linux(self, rootfs=None, bootargs=None):
        """Boot qemu board.

        :param rootfs: parameter to be used at later point, defaults to None.
        :type rootfs: NA
        :param bootargs: parameter to be used at later point, defaults to empty string "".
        :type bootargs: string
        """
        pass

    def reset(self):
        """Reset the qemu board. Use the system_reset command to reset."""
        self.sendcontrol("a")
        self.send("c")
        self.sendline("system_reset")
        self.expect_exact(["system_reset", "Linux version"])
        if "-kernel" not in self.cmd:
            self.expect(["SYSLINUX", "GNU GRUB"])
        self.sendcontrol("a")
        self.send("c")
