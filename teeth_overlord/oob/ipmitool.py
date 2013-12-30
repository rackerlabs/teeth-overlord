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

import structlog
import subprocess
import time

from teeth_overlord.oob import base


POWER_ON = 'Chassis Power Control: Up/On\n'
POWER_OFF = 'Chassis Power Control: Down/Off\n'
POWER_STATE = 'Chassis Power is {}\n'

BOOT_DEVICE = 'Set Boot Device to {}\n'
BOOT_DEVICES = [
    'none',  # Do not change boot device order
    'pxe',  # Force PXE boot
    'disk',  # Force boot from default Hard-drive
    'safe',  # like 'disk', also request safe mode
    'diag',  # Force boot from Diagnostic Partition
    'cdrom',  # Force boot from CD/DVD
    'bios',  # Force boot into BIOS Setup
    'floppy'  # Force boot from Floppy/primary
]


class IPMIToolException(Exception):
    pass


class IPMIToolProvider(base.BaseOutOfBandProvider):

    def __init__(self, config, max_attempts=5, wait_time=0.5):
        super(IPMIToolProvider, self).__init__(config)

        # maximum number of times to try/validate a command
        self.max_attempts = max_attempts
        # wait time between attempts
        self.wait_time = wait_time

        self.log = structlog.get_logger()

    def _wait_for_power_state(self, chassis, state):
        """Checks chassis power state in a loop.

        Returns true when chassis power state matches given state.

        Throws IPMIToolException if self.max_attempts is reached.
        """

        attempts = 0

        while attempts < self.max_attempts:

            attempts = attempts + 1

            chassis_state = self.is_chassis_on(chassis)
            desired_state = state == 'on'
            if chassis_state == desired_state:
                return True
            else:
                if self.wait_time:
                    time.sleep(self.wait_time)

        msg = "power state never changed to {} after {} attempts.".format(
            state, self.max_attempts)
        self.log.error(msg, chassis_id=chassis.id)
        raise IPMIToolException(msg)

    def _exec_ipmitool(self, chassis, command):
        """Formats a command an calls 'ipmitool' targeted at a given chassis.

        Returns 'ipmitool' command stdout
        """

        host = chassis.ipmi_host
        port = str(chassis.ipmi_port)
        username = chassis.ipmi_username
        password = chassis.ipmi_password

        args = [
            'ipmitool',
            '-I', 'lanplus',
            '-H', host,
            '-p', port,
            '-U', username,
            '-P', password
        ]
        args = args + command.split(' ')

        log_dict = {'chassis_id': chassis.id,
                    'host': host,
                    'ipmitool_cmd': ' '.join(args)}

        try:
            self.log.info('executing ipmi command', **log_dict)
            result = subprocess.check_output(args)
            self.log.info('finished ipmi command', result=result, **log_dict)
            return result
        except subprocess.CalledProcessError as e:
            self.log.error('failed ipmi command',
                           exception=str(e),
                           **log_dict)
            raise IPMIToolException(str(e))

    def is_chassis_on(self, chassis):
        """Returns a boolean indicating whether a chassis is on."""

        state = self._exec_ipmitool(chassis, 'power status')

        if state == POWER_STATE.format('on'):
            return True
        elif state == POWER_STATE.format('off'):
            return False
        else:
            msg = 'unknown power state: {}'.format(state)
            self.log.error(msg, chassis_id=chassis.id)
            raise IPMIToolException(msg)

    def power_chassis_off(self, chassis):
        """Power a chassis off."""

        state = self._exec_ipmitool(chassis, 'power off')
        if state == POWER_OFF:
            return self._wait_for_power_state(chassis, 'off')
        else:
            msg = 'unknown power off state: {}'.format(state)
            self.log.error(msg, chassis_id=chassis.id)
            raise IPMIToolException(msg)

    def power_chassis_on(self, chassis):
        """Power a chassis on."""

        state = self._exec_ipmitool(chassis, 'power on')
        if state == POWER_ON:
            return self._wait_for_power_state(chassis, 'on')
        else:
            msg = 'unknown power on state: {}'.format(state)
            self.log.error(msg, chassis_id=chassis.id)
            raise IPMIToolException(msg)

    def set_boot_device(self, chassis, device, persistent=False):
        """Set boot device for next reboot."""

        if device not in BOOT_DEVICES:
            msg = 'unknown boot device: {}'.format(device)
            self.log.error(msg, chassis_id=chassis.id, device=device)
            raise IPMIToolException(msg)

        cmd = "chassis bootdev {}".format(device)
        if persistent:
            cmd = "{} options=persistent".format(cmd)
        state = self._exec_ipmitool(chassis, cmd)

        if state == BOOT_DEVICE.format(device):
            return True
        else:
            msg = "unknown set boot device state: {}".format(state)
            self.log.error(msg, chassis_id=chassis.id, device=device)
            raise IPMIToolException(msg)
