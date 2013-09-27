import os

from twisted.internet.utils import getProcessOutput
from twisted.internet import reactor

user = "ADMIN"
password = "ADMIN"


def set_next_boot_to_pxe(host):
    args = [
        "ipmitool",
        "-U", user,
        "-P", password,
        "-H", host,
        "chassis", "bootdev", "pxe"]

    d = getProcessOutput(
        "ipmitool",
        args=args,
        env={'PATH': os.environ['PATH']})

    return d


def power_cycle(host):
    args = [
        "ipmitool",
        "-U", user,
        "-P", password,
        "-H", host,
        "chassis", "power", "cycle"]

    d = getProcessOutput(
        "ipmitool",
        args=args,
        env={'PATH': os.environ['PATH']})

    return d
