#!/usr/bin/env python
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
import sys

# Borrowed from Heat: https://github.com/openstack/heat/blob/master/bin/heat-api
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]), os.pardir, os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'teeth_overlord', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from cqlengine import connection
from cqlengine.management import sync_table

from teeth_overlord.models import all_models
from teeth_overlord.config import Config
from teeth_overlord.service import global_setup


if __name__ == '__main__':
    global_setup(Config())
    for model in all_models:
        sync_table(model)