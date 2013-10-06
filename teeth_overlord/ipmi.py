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

import os

from twisted.internet.utils import getProcessOutput


def _run_ipmitool(args):

    d = getProcessOutput(
        "ipmitool",
        args=args,
        env={'PATH': os.environ['PATH']})

    return d


def set_next_boot_to_pxe(chassis):
    """
    When run the chassis will boot from network next time
    """

    args = [
        "-U", chassis.ipmi_username,
        "-P", chassis.ipmi_password,
        "-H", chassis.decom_lan_ip,
        "chassis", "bootdev", "pxe"]

    return _run_ipmitool(args)


def power_cycle(chassis):
    """
    Power cycle the chassis
    """

    args = [
        "-U", chassis.ipmi_username,
        "-P", chassis.ipmi_password,
        "-H", chassis.decom_lan_ip,
        "chassis", "power", "cycle"]

    return _run_ipmitool(args)
