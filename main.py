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

import sys

from twisted.internet import reactor
from twisted.python import log

from teeth_overlord.api.server import TeethAPI
from teeth_overlord.config import Config


config = Config()
log.startLogging(sys.stdout)
api = TeethAPI(config)
api.listen()
reactor.run()
