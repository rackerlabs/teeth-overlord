#!/usr/bin/env python

import os
from shipper import Shipper, run, command

DOCKER_HOST = "localhost:4243"
s = Shipper([DOCKER_HOST])

def repo_root():
    return os.path.abspath(os.path.dirname(__file__))

@command
def overlord_base():
    s.build(tag="teeth/overlord_base", path=os.path.join(repo_root(), "overlord_base"))

@command
def overlord():
    s.build(tag="teeth/overlord", path=repo_root())

run()
