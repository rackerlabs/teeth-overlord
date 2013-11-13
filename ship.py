#!/usr/bin/env python

import os
from shipper import Shipper, run, command

DOCKER_HOST = "localhost:4243"
s = Shipper([DOCKER_HOST])

def repo_root():
    return os.path.abspath(os.path.dirname(__file__))

def dependency_path(i):
    return os.path.join(repo_root(), "images", i)

@command
def build_overlord_base():
    s.build(tag="teeth/overlord_base", path=dependency_path("overlord_base"))

@command
def build_cassandra():
    s.build(tag="teeth/cassandra", path=dependency_path("cassandra"))

@command
def build_overlord():
    s.build(tag="teeth/overlord", path=repo_root())

run()
