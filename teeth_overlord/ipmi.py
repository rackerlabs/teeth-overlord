import subprocess

from twisted.internet.utils import getProcessOutput
from twisted.internet import reactor

user = "ADMIN"
password = "ADMIN"


def set_next_boot_to_pxe(host):
    executable = subprocess.check_output('which ipmitool', shell=True).strip()

    args = [
        executable,
        "-U", user,
        "-P", password,
        "-H", host,
        "chassis", "bootdev", "pxe"]

    d = getProcessOutput(executable, args=args)
    return d


def power_cycle(host):
    executable = subprocess.check_output('which ipmitool', shell=True).strip()

    args = [
        executable,
        "-U", user,
        "-P", password,
        "-H", host,
        "chassis", "power", "cycle"]

    d = getProcessOutput(executable, args=args)
    return d
