import subprocess

from twisted.internet.utils import getProcessOutput
from twisted.internet import reactor

user = "ADMIN"
password = "ADMIN"


def set_next_boot_to_pxe(host, callback, errback):
    executable = subprocess.check_output('which ipmi', shell=True).strip()
    arg_string = "-U {} -P {} -H {} chassis bootdev pxe".format(
        user, password, host)

    args = [executable]
    args.extend(arg_string.split(" "))

    d = getProcessOutput(executable, args=args)
    d.addCallback(callback)
    d.addErrback(errback)

    return d


def power_cycle(host, callback, errback):
    executable = subprocess.check_output('which ipmi', shell=True).strip()
    arg_string = "-U {} -P {} -H {} chassis power cycle".format(
        user, password, host)

    args = [executable]
    args.extend(arg_string.split(" "))

    d = getProcessOutput(executable, args=args)
    d.addCallback(callback)
    d.addErrback(errback)

    return d
