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

from uuid import uuid4

import treq
from twisted.internet import threads
from teeth_overlord import models

from teeth_overlord.encoding import TeethJSONEncoder, SerializationViews
from teeth_overlord import errors


class EndpointRPCClient(object):
    """
    Client for interacting with agents via an AgentEndpoint.

    Users of this client call :meth:`get_agent_connection` to locate a
    connection made by the agent to an endpoint, then call other methods
    on this class, passing in the agent connection as well as any
    method-specific parameters. This client will perform a call to the
    REST API exposed by the Agent Endpoint, which will in turn perform
    the desired command on the agent and return the result.
    """
    def __init__(self, config):
        self.encoder = TeethJSONEncoder(SerializationViews.PUBLIC)
        self.config = config

    def _get_command_url(self, connection):
        return 'http://{host}:{port}/v1.0/agent_connections/{connection_id}/command'.format(
            host=connection.endpoint_rpc_host,
            port=connection.endpoint_rpc_port,
            connection_id=connection.id
        )

    def _get_command_body(self, method, params):
        return self.encoder.encode({
            'method': method,
            'params': params,
        })

    def _command(self, connection, method, params):
        url = self._get_command_url(connection)
        body = self._get_command_body(method, params)
        headers = {
            'Content-Type': 'application/json'
        }
        return treq.post(url, data=body, headers=headers).addCallback(treq.json_content)

    def get_agent_connection(self, chassis):
        """
        Retrieve an agent connection for the specified Chassis.
        """
        def _with_connection(connection):
            if not connection:
                raise errors.AgentNotConnectedError(chassis.id, chassis.primary_mac_address)
            return connection

        connection_query = models.AgentConnection.objects
        connection_query = connection_query.filter(primary_mac_address=chassis.primary_mac_address)
        return threads.deferToThread(connection_query.first).addCallback(_with_connection)

    def prepare_image(self, connection, image_id):
        """
        Call the `prepare_image` method on the agent.
        """
        return self._command(connection, 'prepare_image', {
            'task_id': str(uuid4()),
            'image_id': image_id,
        })
