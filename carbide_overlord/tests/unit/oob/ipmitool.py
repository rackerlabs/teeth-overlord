"""
Copyright 2013 Rackspace, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import mock
import subprocess

from teeth_overlord import models
from teeth_overlord import tests

from teeth_overlord.oob import ipmitool


class TestIPMIToolDriver(tests.TeethMockTestUtilities):

    def setUp(self):
        super(TestIPMIToolDriver, self).setUp()

        self.chassis1 = models.Chassis(id='chassis1',
                                       state=models.ChassisState.READY,
                                       primary_mac_address='1:2:3:4:5',
                                       ipmi_host='1.2.3.4',
                                       ipmi_port=623,
                                       ipmi_username='ipmi_user',
                                       ipmi_password='ipmi_pass')

        self.ipmi_call_args = [
            'ipmitool',
            '-I', 'lanplus',
            '-H', self.chassis1.ipmi_host,
            '-p', str(self.chassis1.ipmi_port),
            '-U', self.chassis1.ipmi_username,
            '-P', self.chassis1.ipmi_password
        ]

        patcher = mock.patch.object(subprocess, 'check_output')
        self.subprocess_mock = patcher.start()
        self.addCleanup(patcher.stop)

        self.ipmitool_provider = ipmitool.IPMIToolProvider(None,
                                                           max_attempts=2,
                                                           wait_time=0.0)

    def test_is_chassis_on(self):
        self.subprocess_mock.return_value = 'Chassis Power is on\n'

        on = self.ipmitool_provider.is_chassis_on(self.chassis1)

        self.assertTrue(on)
        self.subprocess_mock.assert_called_once_with(self.ipmi_call_args +
                                                     ['power', 'status'])

    def test_is_chassis_off(self):

        self.subprocess_mock.return_value = 'Chassis Power is off\n'

        on = self.ipmitool_provider.is_chassis_on(self.chassis1)

        self.assertFalse(on)
        self.subprocess_mock.assert_called_once_with(self.ipmi_call_args +
                                                     ['power', 'status'])

    def test_is_chassis_on_unknown_state(self):
        self.subprocess_mock.return_value = 'Unknown State\n'

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.is_chassis_on,
                          self.chassis1)

        self.subprocess_mock.assert_called_once_with(self.ipmi_call_args +
                                                     ['power', 'status'])

    def test_is_chassis_on_error(self):

        self.subprocess_mock.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="foo", output="bar")

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.is_chassis_on,
                          self.chassis1)

        self.subprocess_mock.assert_called_once_with(self.ipmi_call_args +
                                                     ['power', 'status'])

    def test_power_on(self):
        self.subprocess_mock.side_effect = [
            'Chassis Power Control: Up/On\n',
            'Chassis Power is off\n',
            'Chassis Power is on\n'
        ]

        on = self.ipmitool_provider.power_chassis_on(self.chassis1)

        self.assertTrue(on)
        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'on'])
        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'status'])
        self.assertEqual(self.subprocess_mock.call_count, 3)

    def test_power_off(self):
        self.subprocess_mock.side_effect = [
            'Chassis Power Control: Down/Off\n',
            'Chassis Power is on\n',
            'Chassis Power is off\n'
        ]

        on = self.ipmitool_provider.power_chassis_off(self.chassis1)

        self.assertTrue(on)
        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'off'])
        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'status'])
        self.assertEqual(self.subprocess_mock.call_count, 3)

    def test_power_on_failure(self):
        self.subprocess_mock.side_effect = [
            'Chassis Power Control: Up/On\n',
            'Chassis Power is off\n',
            'Chassis Power is off\n'
        ]

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.power_chassis_on,
                          self.chassis1)

        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'on'])
        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'status'])
        self.assertEqual(self.subprocess_mock.call_count, 3)

    def test_power_off_failure(self):
        self.subprocess_mock.side_effect = [
            'Chassis Power Control: Down/Off\n',
            'Chassis Power is on\n',
            'Chassis Power is on\n'
        ]

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.power_chassis_off,
                          self.chassis1)

        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'off'])
        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'status'])
        self.assertEqual(self.subprocess_mock.call_count, 3)

    def test_power_on_error(self):
        self.subprocess_mock.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="foo", output="bar")

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.power_chassis_on,
                          self.chassis1)
        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'on'])
        self.assertEqual(self.subprocess_mock.call_count, 1)

    def test_power_off_error(self):
        self.subprocess_mock.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="foo", output="bar")

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.power_chassis_off,
                          self.chassis1)
        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'off'])
        self.assertEqual(self.subprocess_mock.call_count, 1)

    def test_power_on_unknown_state(self):
        self.subprocess_mock.side_effect = ['Unknown State\n']

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.power_chassis_on,
                          self.chassis1)

        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'on'])
        self.assertEqual(self.subprocess_mock.call_count, 1)

    def test_power_off_unknown_state(self):
        self.subprocess_mock.side_effect = ['Unknown State\n']

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.power_chassis_off,
                          self.chassis1)

        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['power', 'off'])
        self.assertEqual(self.subprocess_mock.call_count, 1)

    def test_set_boot_device(self):
        self.subprocess_mock.return_value = 'Set Boot Device to pxe\n'

        on = self.ipmitool_provider.set_boot_device(self.chassis1, 'pxe')

        self.assertTrue(on)
        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['chassis', 'bootdev', 'pxe'])
        self.assertEqual(self.subprocess_mock.call_count, 1)

    def test_set_boot_device_persistent(self):
        self.subprocess_mock.return_value = 'Set Boot Device to pxe\n'

        on = self.ipmitool_provider.set_boot_device(
            self.chassis1, 'pxe', persistent=True)

        self.assertTrue(on)
        self.subprocess_mock.assert_any_call(
            self.ipmi_call_args + ['chassis',
                                   'bootdev',
                                   'pxe',
                                   'options=persistent'])
        self.assertEqual(self.subprocess_mock.call_count, 1)

    def test_set_boot_device_invalid_device(self):
        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.set_boot_device,
                          self.chassis1, 'foobar')

        self.assertEqual(self.subprocess_mock.call_count, 0)

    def test_set_boot_device_unknown_state(self):
        self.subprocess_mock.return_value = 'Unknown State\n'

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.set_boot_device,
                          self.chassis1, 'pxe')

        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['chassis', 'bootdev', 'pxe'])
        self.assertEqual(self.subprocess_mock.call_count, 1)

    def test_set_boot_device_error(self):
        self.subprocess_mock.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="foo", output="bar")

        self.assertRaises(ipmitool.IPMIToolException,
                          self.ipmitool_provider.set_boot_device,
                          self.chassis1, 'pxe')

        self.subprocess_mock.assert_any_call(self.ipmi_call_args +
                                             ['chassis', 'bootdev', 'pxe'])
        self.assertEqual(self.subprocess_mock.call_count, 1)
