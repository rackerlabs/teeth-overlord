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

from zope.interface import implements
from twisted.python import usage
from twisted.application.service import IServiceMaker
from twisted.plugin import IPlugin

from teeth_overlord.config import Config

class TeethServiceOptions(usage.Options):
    optParameters = [
        ['config', 'c', None, 'Path to the config file to use.'],
    ]


class TeethServiceMaker(object):
    implements(IServiceMaker, IPlugin)

    tapname = 'teeth-public-api'
    description = 'Teeth public API service'
    options = TeethServiceOptions

    def __init__(self, service_class, tapname, description):
        self.service_class = service_class
        self.tapname = tapname
        self.description = description
    
    def makeService(self, options):
        config_path = options.get('config', None)
        if config_path:
            return self.service_class(Config.from_json_file(config_path))
        else:
            return self.service_class(Config())
