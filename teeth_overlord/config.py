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

import simplejson as json
from cqlengine import connection


class Config(object):
    CASSANDRA_CLUSTER = ['127.0.0.1:9160']
    CASSANDRA_CONSISTENCY = 'ONE'
    API_HOST = 'localhost'
    API_PORT = 8080
    AGENT_ENDPOINT_AGENT_HOST = 'localhost'
    AGENT_ENDPOINT_AGENT_PORT = 8081
    AGENT_ENDPOINT_RPC_HOST = 'localhost'
    AGENT_ENDPOINT_RPC_PORT = 8082

    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            if key in self:
                self[key] = value

        connection.setup(self.CASSANDRA_CLUSTER,
                         consistency=self.CASSANDRA_CONSISTENCY)

    @classmethod
    def from_json_file(cls, config_path):
        return cls(**json.loads(open(config_path, 'r').read()))