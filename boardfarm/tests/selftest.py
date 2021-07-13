"""Test/Validate the behaviour of new/modified components.

This file can be used to add unit tests that
tests/validate the behavior of new/modified
components.
"""
import hashlib
import os
import random
import string
import tempfile

import pytest

from boardfarm import lib
from boardfarm.devices import debian, linux
from boardfarm.lib import ConfigHelper, SnmpHelper, common
from boardfarm.orchestration import TestStep as TS
from boardfarm.tests import rootfs_boot


@pytest.mark.selftest
class selftest_test_copy_file_to_server(rootfs_boot.RootFSBootTest):
    """Copy a file to /tmp on the WAN device using\
    common.copy_file_to_server."""

    def test_main(self):
        """Copy a file to /tmp on the WAN device using\
        common.copy_file_to_server."""
        wan = self.dev.wan

        if not wan:
            msg = "No WAN Device defined, skipping copy file to WAN test."
            lib.common.test_msg(msg)
            self.skipTest(msg)

        if not hasattr(wan, "ipaddr"):
            msg = "WAN device is not running ssh server, can't copy with this function"
            lib.common.test_msg(msg)
            self.skipTest(msg)
        text_file = tempfile.NamedTemporaryFile(mode="w")
        self.fname = fname = text_file.name

        letters = string.ascii_letters
        fcontent = "".join(random.choice(letters) for _ in range(50))

        text_file.write(fcontent)
        text_file.flush()

        fmd5 = hashlib.md5(open(fname, "rb").read()).hexdigest()
        print(f"File original md5sum: {fmd5}")

        cmd = (
            'cat %s | ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p %s -x %s@%s "cat - > %s"'
            % (fname, wan.port, wan.username, wan.ipaddr, fname)
        )
        # this must fail as the command does not echo the filename
        try:
            common.copy_file_to_server(cmd, wan.password, "/tmp")
        except Exception:
            print("Copy failed as expected")

        cmd = (
            'cat %s | ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p %s -x %s@%s "cat - > %s; echo %s"'
            % (fname, wan.port, wan.username, wan.ipaddr, fname, fname)
        )
        # this should pass
        try:
            common.copy_file_to_server(cmd, wan.password, "/tmp")
        except Exception:
            assert 0, "copy_file_to_server failed, Test failed!!!!"

        # is the destination file identical to the source file
        wan.sendline(f"md5sum {fname}")
        wan.expect(fmd5)
        wan.expect(wan.prompt)

        print("Test passed")


@pytest.mark.selftest
class selftest_test_create_session(rootfs_boot.RootFSBootTest):
    """tests the create_session function in devices/__init__.py."""

    session = None

    def test_main(self):
        """Tests the create_session function in devices/__init__.py."""
        wan = self.dev.wan

        if not wan:
            msg = "No WAN Device defined, skipping test_create_session."
            lib.common.test_msg(msg)
            self.skipTest(msg)

        from boardfarm import devices

        # this should fail, as "DebianBoxNonExistent" is not (yet) a device
        try:
            kwargs = {
                "name": "wan_test_calls_fail",
                "ipaddr": wan.ipaddr,
                "port": 22,
                "color": "magenta",
            }
            self.session = devices.get_device(
                "DebianBoxNonExistent", device_mgr=self.dev, **kwargs
            )
        except Exception as e:
            print(e)
        else:
            assert self.session is None, "Test Failed on wrong class name"
            print("Failed to create session on wrong class name (expected) PASS")

        # this must fail, as "169.254.12.18" is not a valid ip
        try:
            kwargs = {
                "name": "wan_test_ip_fail",
                "ipaddr": "169.254.12.18",
                "port": 22,
                "color": "cyan",
            }
            self.session = devices.get_device(
                "DebianBox", device_mgr=self.dev, **kwargs
            )
        except Exception as e:
            print(e)
        else:
            assert self.session is None, "Test Failed on wrong IP"
            print("Failed to create session on wrong IP (expected) PASS")

        # this must fail, as 50 is not a valid port
        try:
            kwargs = {
                "name": "wan_test_port_fail",
                "ipaddr": wan.ipaddr,
                "port": 50,
                "color": "red",
            }
            self.session = devices.get_device(
                "DebianBox", device_mgr=self.dev, **kwargs
            )
        except Exception as e:
            print(e)
        else:
            assert self.session is None, "Test Failed on wrong port"
            print("Failed to create session on wrong port (expected) PASS")

        # this must fail, close but no cigar
        try:
            kwargs = {
                "name": "wan_test_type_fail",
                "ipaddr": wan.ipaddr,
                "port": 50,
                "color": "red",
            }
            self.session = devices.get_device("debina", device_mgr=self.dev, **kwargs)
        except Exception as e:
            print(e)
        else:
            assert self.session is None, "Test Failed on misspelled class name"
            print("Failed to create session on misspelled class name (expected) PASS")

        # this should pass
        try:
            kwargs = {
                "name": "correct_wan_parms",
                "ipaddr": wan.ipaddr,
                "port": wan.port,
                "color": "yellow",
            }
            self.session = devices.get_device(
                "debian", device_mgr=self.dev, override=True, **kwargs
            )
        except Exception:
            assert 0, "Failed to create session, Test FAILED!"
        else:
            assert self.session is not None, "Test Failed on correct parameters!!"

        print("Session created successfully")

        # is the session really logged onto the wan?

        wan.sendline()
        wan.expect(wan.prompt)
        wan.sendline("ip a")
        wan.expect_exact("ip a")
        wan.expect(wan.prompt)
        w = wan.before

        self.session.sendline()
        self.session.expect(self.session.prompt)
        self.session.sendline("ip a")
        self.session.expect_exact("ip a")
        self.session.expect(self.session.prompt)
        s = self.session.before

        assert w == s, "Interfaces differ!!! Test Failed"

        self.session.sendline("exit")

        print("Test passed")

    def recover(self):
        """Exit from prompt if session is not empty."""
        if self.session is not None:
            self.session.sendline("exit")


@pytest.mark.selftest
class selftest_testing_linuxdevice_functions(rootfs_boot.RootFSBootTest):
    """tests the linux functions moved to devices/linux.py."""

    def test_main(self):
        """Tests the linux functions moved to devices/linux.py."""
        board = self.dev.board
        lan = self.dev.lan

        if lan.model == "debian":
            # check that lan is derived from LinuxDevice
            assert issubclass(debian.DebianBox, linux.LinuxDevice)

        # get the mac address of the interface
        lan_mac = lan.get_interface_macaddr(lan.iface_dut)
        assert lan_mac is not None, "Failed getting lan mac address"
        print(f"lan mac address: {lan_mac}")

        # check the system uptime
        uptime = lan.get_seconds_uptime()
        assert uptime is not None, "Failed getting system uptime"
        print(f"system uptime is: {uptime}")

        # ping ip using function ping from linux.py
        ping_check = lan.ping("8.8.8.8")
        print(f"ping status is {ping_check}")

        # disable ipv6
        lan.disable_ipv6(lan.iface_dut)
        # enable ipv6
        lan.enable_ipv6(lan.iface_dut)
        board.set_printk()
        print("Test passed")

        # remove neighbour table entries
        lan.ip_neigh_flush()

        # set the link state up
        lan.set_link_state(lan.iface_dut, "up")

        # Checking the interface status
        link = lan.is_link_up(lan.iface_dut)
        assert link is not None, "Failed to check the link is up"

        # add sudo when the username is root
        lan.sudo_sendline("ping -c5 '8.8.8.8'")
        lan.expect(lan.prompt, timeout=50)

        # add new user name in linux
        lan.add_new_user("test", "test")
        lan.sendline("userdel test")
        lan.expect(lan.prompt)

        text_file = tempfile.NamedTemporaryFile(mode="w")
        letters = string.ascii_letters
        fcontent = "".join(random.choice(letters) for _ in range(50))

        text_file.write(fcontent)
        text_file.flush()

        fmd5 = hashlib.md5(open(text_file.name, "rb").read()).hexdigest()
        print(f"File original md5sum: {fmd5}")
        print("copying file to lan at /tmp/dst.txt")
        lan.copy_file_to_server(text_file.name, "/tmp/dst.txt")
        print("Copy Done. Verify the integrity of the file")
        lan.sendline("md5sum /tmp/dst.txt")
        lan.expect(fmd5)
        lan.expect(lan.prompt)
        """FUnctions moved from openwrt to linux """
        # Wait until network interfaces have IP Addresses
        board.wait_for_network()
        print("Waited until network interfaces has ip address")

        # Check the available memory of the device
        memory_avail = board.get_memfree()
        print(f"Available memory of the device:{memory_avail}")

        # Getting the vmstat
        vmstat_out = board.get_proc_vmstat()
        assert vmstat_out is not None, "virtual machine status is None"
        print(f"Got the vmstat{vmstat_out}")

        # Get the total number of connections in the network
        nw_count = board.get_nf_conntrack_conn_count()
        assert nw_count is not None, "connections are empty"
        print(f"Get the total number of connections in the network{nw_count}")

        # Getting the DNS server upstream
        ip_addr = board.get_dns_server_upstream()
        assert ip_addr is not None, "Getting nameserver ip is None"
        print(f"Got the DNS server upstream{ip_addr}")
        print("Test Passed")


class SnmpMibsUnitTest:
    """
    Unit test for the SnmpMibs class.

    Check for correct and incorrect mibs.
    Default assumes the .mib files are in $USER/.snmp
    DEBUG:
    BFT_DEBUG=y     shows the compiled dictionary
    BFT_DEBUG=yy    VERY verbose, shows the compiled dictionary and
    mibs/oid details
    """

    error_mibs = [
        "SsnmpEngineMaxMessageSize",  # misspelled MUST fail
        "nonExistenMib",  # this one MUST fail
        "ifCounterDiscontinuityTimeQ",
    ]  # misspelled MUST fail

    mibs = [
        "docsDevSwAdminStatus",
        "snmpEngineMaxMessageSize",
        error_mibs[0],
        "docsDevServerDhcp",
        "ifCounterDiscontinuityTime",
        error_mibs[1],
        "docsBpi2CmtsMulticastObjects",
        error_mibs[2],
    ]

    mib_files = [
        "DOCS-CABLE-DEVICE-MIB",
        "DOCS-IETF-BPI2-MIB",
    ]  # this is the list of mib/txt files to be compiled
    src_directories = [
        "/tmp/boardfarm-docsis/mibs"
    ]  # this needs to point to the mibs directory location
    snmp_obj = None  # will hold an instance of the  SnmpMibs class

    def __init__(self, mibs_location=None, files=None, mibs=None, err_mibs=None):
        """Initialize the SnmpMibsUnitTest class.

        Takes:
            mibs_location:  where the .mib files are located (can be a list of dirs)
            files:          the name of the .mib/.txt files (without the extension)
            mibs:           e.g. sysDescr, sysObjectID, etc
            err_mibs:       wrong mibs (just for testing that the compiler rejects invalid mibs)
        """
        # where the .mib files are located
        if mibs_location:
            self.src_directories = mibs_location

        if type(self.src_directories) != list:
            self.src_directories = [self.src_directories]

        for d in self.src_directories:
            if not os.path.exists(str(d)):
                msg = "No mibs directory {} found test_SnmpHelper.".format(
                    str(self.src_directories)
                )
                raise Exception(msg)

        if files:
            self.mib_files = files

        self.snmp_obj = SnmpHelper.SnmpMibs.get_mib_parser(
            self.mib_files, self.src_directories
        )
        print(f"Using class singleton: {self.snmp_obj!r}")

        # the SAME object should be returned, NOT A NEW/DIFFERENT ONE!!!!!
        assert self.snmp_obj is SnmpHelper.SnmpMibs.get_mib_parser(
            self.mib_files, self.src_directories
        ), "SnmpHelper.SnmpMibs.get_mib_parser returned a NEW/different object. FAILED"
        print("SnmpHelper.SnmpMibs.get_mib_parser returned the same object PASS")

        # the same must be true when using the property method
        assert (
            self.snmp_obj is SnmpHelper.SnmpMibs.default_mibs
        ), "SnmpHelper.SnmpMibs.default_mibs returned a NEW/different object. FAILED"
        print("SnmpHelper.SnmpMibs.default_mibs returned the same object PASS")

        if mibs:
            self.mibs = mibs
            self.error_mibs = err_mibs

        if type(self.mibs) != list:
            self.mibs = [self.mibs]

    def unitTest(self):
        """Compile the ASN1 and gets the oid of the given mibs.

        Asserts on failure
        """
        if "y" in self.snmp_obj.dbg:
            print(f"The SNMP mib_dict contains {len(self.snmp_obj.mib_dict)} keys.")
            print("First 5 mib_dict keys and values alphabetically:")
            for k in sorted(self.snmp_obj.mib_dict)[:5]:
                print(f"{k}: {self.snmp_obj.mib_dict[k]}")

        # used in the second round of testing (i.e. the get oid without the obj)
        self.mibs1 = self.mibs[:]
        self.error_mibs1 = self.error_mibs[:]

        print(
            "=================================================================================="
        )
        print("Testing getting a mib oid with method off the parser obj")
        for i in self.mibs:
            try:
                oid = self.snmp_obj.get_mib_oid(i)
                print(f"parse.get_mib_oid({i}) - oid={oid}")

            except Exception as e:
                print(e)
                # we should NOT find only the errored mibs, all other mibs MUST be found
                assert i in self.error_mibs, "Failed to get oid for mib: " + i
                print(f"Failed to get oid for mib: {i} (expected)")
                if self.error_mibs is not None:
                    self.error_mibs.remove(i)

        # the unit test must find all the errored mibs!
        if self.error_mibs is not None:
            assert (
                self.error_mibs == []
            ), f"The test missed the following mibs: {str(self.error_mibs)}"

        print(
            "=================================================================================="
        )
        print(
            "Testing getting a mib oid with public method (without having to get the obj first)"
        )
        from boardfarm.lib.SnmpHelper import get_mib_oid

        for i in self.mibs1:
            try:
                oid = get_mib_oid(i)
                print(f"get_mib_oid({i}) - oid={oid}")

            except Exception as e:
                print(e)
                # we should NOT find only the errored mibs, all other mibs MUST be found
                assert i in self.error_mibs1, "Failed to get oid for mib: " + i
                print(f"Failed to get oid for mib: {i} (expected)")
                if self.error_mibs1 is not None:
                    self.error_mibs1.remove(i)

        # the unit test must find all the errored mibs!
        if self.error_mibs1 is not None:
            assert (
                self.error_mibs1 == []
            ), f"The test missed the following mibs: {str(self.error_mibs1)}"

        return True


class selftest_test_SnmpHelper(rootfs_boot.RootFSBootTest):
    """Test the SnmpHelper module.

    Tests the SnmpHelper module:
    1. compiles and get the oid of some sample mibs
    2. performs an snmp get from the lan to the wan
    using the compiled oids
    """

    def test_main(self):
        """Start testing the SnmpHelper module."""
        wan = self.dev.wan
        lan = self.dev.lan

        from boardfarm.lib.common import snmp_mib_get
        from boardfarm.lib.installers import install_snmp, install_snmpd

        wrong_mibs = ["PsysDescr", "sys123ObjectID", "sysServiceS"]
        linux_mibs = [
            "sysDescr",
            "sysObjectID",
            "sysServices",
            "sysName",
            "sysServices",
            "sysUpTime",
        ]

        test_mibs = [
            linux_mibs[0],
            wrong_mibs[0],
            linux_mibs[1],
            wrong_mibs[1],
            linux_mibs[2],
            wrong_mibs[2],
        ]

        unit_test = SnmpMibsUnitTest(
            mibs_location=os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    os.pardir,
                    "resources",
                    "mibs",
                )
            ),
            files=["SNMPv2-MIB"],
            mibs=test_mibs,
            err_mibs=wrong_mibs,
        )
        assert unit_test.unitTest()

        install_snmpd(wan)

        lan.sendline('echo "nameserver 8.8.8.8" >> /etc/resolv.conf')
        lan.expect(lan.prompt)

        install_snmp(lan)
        wan_iface_ip = wan.get_interface_ipaddr(wan.iface_dut)

        for mib in linux_mibs:
            try:
                result = snmp_mib_get(
                    lan,
                    unit_test.snmp_obj,
                    str(wan_iface_ip),
                    mib,
                    "0",
                    community="public",
                )

                print(f"snmpget({mib})@{wan_iface_ip}={result}")
                print("Trying with snmp_v2 as well")

                value = SnmpHelper.snmp_v2(
                    lan, str(wan_iface_ip), mib, community="public"
                )

                print(f"Snmpget via snmpv2 on {mib}: {value}")

            except Exception as e:
                print(f"Failed on snmpget {mib} ")
                print(e)
                raise e

        print("Test passed")


class selftest_test_retry(rootfs_boot.RootFSBootTest):
    """Fails N times before passing, to test the retry function."""

    fail_on = 0
    runs = 0

    def test_main(self):
        """Start testing the retry function."""
        if not self.config.retry:
            self.skipTest("Test needs to be rerun with retries")

        assert self.fail_on != 0, "fail_on must be greater than 1"

        runs = self.runs
        self.runs = runs + 1

        assert runs == self.fail_on, "Planned failure of test"


class selftest_test_retry_1(selftest_test_retry):
    """Fails 1 times before passing, to test the retry function."""

    fail_on = 1


class selftest_test_retry_2(selftest_test_retry):
    """Fails 2 times before passing, to test the retry function."""

    fail_on = 2


class selftest_test_retry_3(selftest_test_retry):
    """Fails 3 times before passing, to test the retry function."""

    fail_on = 3


class selftest_always_fail(rootfs_boot.RootFSBootTest):
    """This test always fails, for testing bft core code."""

    expected_failure = True

    def test_main(self):
        """Print failing message and assert False."""
        print("Failing...")
        assert False


class selftest_err_injection(rootfs_boot.RootFSBootTest):
    """Simple harness to tests that the error injection intercepts\
    the function calls and spoofs the return value.

    The dictionary must be given via command line using the --err argument, some examples:
    --err "http://<some web addr>/error_injection.json".
    --err "path_to/error_injection.json".

    for multiple sources (or web) a dict.update() is performed:

    --err "path_to/error_injection.json" "path_to/error_injection1.json".

    For this selftest the following json is needed:
    {
    "selftest_err_injection":
    {
    "simple_bool_return":false,
    "get_dev_ip_address":"169.254.1.3"
    }
    }
    """

    def simple_bool_return(self):
        """Return true when invoked."""
        return True

    def get_dev_ip_address(self, dev):
        """Get the device ip address."""
        return dev.get_interface_ipaddr(dev.iface_dut)

    def err_inj_prep(self):
        if not ConfigHelper()["err_injection_dict"]:
            print("err_injection_dict not found... Skipping test")
            self.skipTest("err_injection_dict not found!!!")

        self.cls_name = self.__class__.__name__

    def test_main(self):
        """Start testing the error injection intercepts the function call\
        and spoof the return value."""
        lan = self.dev.lan

        expected_faulures = 0

        self.err_inj_prep()

        assert not self.simple_bool_return(), "error not correctly injected"
        ConfigHelper()["err_injection_dict"][self.cls_name].pop("simple_bool_return")
        print("simple_bool_return spoofed PASS")

        assert self.simple_bool_return(), "real value not received"
        print("simple_bool_return real value PASS")

        addr = self.get_dev_ip_address(lan)
        assert (
            addr
            == ConfigHelper()["err_injection_dict"][self.cls_name]["get_dev_ip_address"]
        ), "spoofed value not received"
        print(f"received spoofed address: {str(addr)}")
        print("get_dev_ip_address spoofed PASS")

        addr = self.get_dev_ip_address(lan)
        try:
            assert addr == lan.get_interface_ipaddr(lan.iface_dut)
            print(f"get_dev_ip_address: {str(addr)}, UNEXPECTED FAILURE!!!! ")
        except Exception:
            print(f"get_dev_ip_address: {str(addr)}, EXPECTED FAILURE")
            expected_faulures += 1
        ConfigHelper()["err_injection_dict"][self.cls_name].pop("get_dev_ip_address")
        assert (
            expected_faulures
        ), "get_dev_ip_address spoofed with EXPECTED FAILURE PASS"

        addr = self.get_dev_ip_address(lan)
        assert addr == lan.get_interface_ipaddr(
            lan.iface_dut
        ), "spoofed value not received"
        print(f"received real address: {addr}")
        print("get_dev_ip_address real PASS")

        # just  for the sake of this test we check that all the errors have been injected
        # this may not be the case a real world scenario
        assert not ConfigHelper()["err_injection_dict"][
            self.cls_name
        ], "Not all errors were injected"
        print("all errors have been injected")

        print(f"{self.cls_name}: PASS")


class selftest_tear_down(rootfs_boot.RootFSBootTest):
    """A sample test class to validate teardown feature.

    Need to ensure that teardown marks the test as fail,
    when an action added to teardown fails.
    """

    def action_1(self, arg1):
        """Print the arg1 values."""
        print(arg1)
        print(type(arg1))

    def teardown_action1(self):
        """Execute teardown_action1 successfully and return True."""
        print("This is teardown action1. This executes successfully")
        return True

    def teardown_action2(self):
        """Cause an error and mark test as FAIL."""
        print("This is teardown action2. This will coz an error and mark test as FAIL")
        raise ValueError("No arguments passed to the test")

    def test_main(self):
        """A sample test class to validate teardown feature."""
        with TS(self, "TD selftest. Print action1 output") as ts:
            ts.call(self.action_1, "Executed Action 1")

    @classmethod
    def teardown_class(cls):
        """Call teardown_action1 method for teardown."""
        obj = cls.test_obj
        cls.call(obj.teardown_action1)
