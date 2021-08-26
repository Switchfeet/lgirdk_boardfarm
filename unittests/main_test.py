#!/usr/bin/env python3

import os
import unittest
from copy import deepcopy

import boardfarm


class TestSimpleBoardfarm(unittest.TestCase):
    def test_import_tests(self):
        """
        Verify we can import all boardfarm tests.
        """
        from boardfarm import tests

        tests.init(None)
        # Also make sure something is in tests.available_tests
        self.assertGreater(len(tests.available_tests), 10)

    def test_import_debian_wifi(self):
        """
        Verify we can import a specific device by name.
        """
        import boardfarm.devices.debian_wifi

        print(boardfarm.devices.debian_wifi.__name__)

    def test_devicemanager(self):
        """
        Verify we can add devices and get one back by type.
        """
        from boardfarm.lib import DeviceManager

        class FakeDevice:
            def __init__(self, name):
                self.name = name

        dev1 = FakeDevice(name="board")
        dev2 = FakeDevice(name="lan")
        # Add devices to DeviceManager
        mgr = deepcopy(DeviceManager.device_manager())
        mgr._add_device(dev1)
        mgr._add_device(dev2)
        # Get a device back
        x = mgr.by_type(DeviceManager.device_type.lan)
        self.assertEqual("lan", x.name)
        # Get a device by the convience attribute
        y = mgr.lan
        self.assertEqual("lan", y.name)
        self.assertIn("board", dir(mgr))

    def test_devicemanager_devicenone(self):
        """
        Verify we can get a default device from device manager
        when it doesn't have a real device of that type.
        """
        from boardfarm.lib import DeviceManager

        mgr = deepcopy(DeviceManager.device_manager())
        # Ask for device it doesn't have
        x = mgr.by_type(DeviceManager.device_type.fax_modem)
        self.assertEqual(x.__class__.__name__, "DeviceNone")

    def test_board_filter(self):
        """
        Verify regular-expression match filter for boards works.
        """
        from boardfarm.lib import test_configurator

        # Fake station
        conf = {"type": "raspberrypi", "features": "wifi"}
        # Should return true because it has 'wifi'
        result = test_configurator.filter_boards(conf, "wifi")
        self.assertEqual(result, True)
        # Should return false because it doesn't have 'lasers'
        result = test_configurator.filter_boards(conf, "lasers")
        self.assertEqual(result, False)

    def test_kibana_datagen(self):
        from boardfarm.library import generate_test_info_for_kibana, get_test_name

        class Dummy:
            logged = {}
            result_grade = "OK"

        x = Dummy()
        x.override_kibana_name = "Testing123"
        data = generate_test_info_for_kibana(x, prefix="Hello")
        self.assertEqual(x.override_kibana_name, get_test_name(x))
        self.assertIn("HelloTesting123-result", data)

    def test_station_filtering(self):
        from boardfarm.lib import test_configurator

        cur_dir = os.path.dirname(boardfarm.__file__)
        loc, conf = test_configurator.get_station_config(
            os.path.join(cur_dir, "boardfarm_config_example.json")
        )
        names = test_configurator.filter_station_config(conf, board_type=["qemux86"])
        self.assertGreater(len(names), 0)
        names = test_configurator.filter_station_config(
            conf, board_type=["qemux86"], board_filter="local"
        )
        self.assertGreater(len(names), 0)

    def test_skip_on_fail_decorator(self):
        from boardfarm.tests.bft_base_test import BftBaseTest
        from boardfarm.tests_wrappers import skip_on_fail

        global ran
        ran = False

        class test_stub(BftBaseTest):
            log_to_file = ""

            def test_main(self):
                pass

            def skipTest(self, msg):
                print("skipTest() called")
                global ran
                ran = True

                super().skipTest(msg)

        @skip_on_fail
        def test_func(test, arg1, arg2):
            if arg1 != arg2:
                print("skipTest() should be called")
            assert arg1 == arg2

        test_func(test_stub(None, None, None), "same", "same")
        self.assertEqual(ran, False)
        with self.assertRaises(boardfarm.exceptions.BftDeprecate):
            test_func(test_stub(None, None, None), "not", "same")
            self.assertEqual(ran, True)


if __name__ == "__main__":
    # Run all tests by typing one command:
    #     ./main.py -v
    unittest.main()
