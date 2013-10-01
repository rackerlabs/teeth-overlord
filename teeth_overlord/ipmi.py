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
