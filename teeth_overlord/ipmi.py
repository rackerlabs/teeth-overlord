import os

from twisted.internet.utils import getProcessOutput


def _run_ipmitool(ars):

    d = getProcessOutput(
        "ipmitool",
        args=args,
        env={'PATH': os.environ['PATH']})

    return d


def set_next_boot_to_pxe(chassis):
    args = [
        "ipmitool",
        "-U", chassis.ipmi_username,
        "-P", chassis.ipmi_password,
        "-H", chassis.decom_lan_ip,
        "chassis", "bootdev", "pxe"]

    return _run_ipmitool(args)


def power_cycle(chassis):
    args = [
        "ipmitool",
        "-U", chassis.ipmi_username,
        "-P", chassis.ipmi_password,
        "-H", chassis.decom_lan_ip,
        "chassis", "power", "cycle"]

    return _run_ipmitool(args)
