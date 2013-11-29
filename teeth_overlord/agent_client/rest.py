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

import json

import requests

from teeth_overlord import errors
from teeth_overlord.encoding import TeethJSONEncoder, SerializationViews
from teeth_overlord.models import AgentConnection
from teeth_overlord.agent_client.base import BaseAgentClient


class RESTAgentClient(BaseAgentClient):
    """
    Client for interacting with agents via a REST API.
    """
    def __init__(self, config):
        super(RESTAgentClient, self).__init__(config)
        self.encoder = TeethJSONEncoder(SerializationViews.PUBLIC)
        self.session = requests.Session()

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
        response = self.session.post(url, data=body, headers=headers)

        # TODO: real error handling
        return json.loads(response.text)

    def get_agent_connection(self, chassis):
        """
        Retrieve an agent connection for the specified Chassis.
        """
        query = AgentConnection.objects.filter(primary_mac_address=chassis.primary_mac_address)

        try:
            return query.get()
        except AgentConnection.DoesNotExist:
            raise errors.AgentNotConnectedError(chassis.id, chassis.primary_mac_address)

    def cache_images(self, connection, image_ids):
        """
        Attempt to cache the specified images. Images are specified in
        priority order, and may not all be cached.
        """
        return self._command(connection, 'standby.cache_images', {
            'task_id': self.new_task_id(),
            'image_ids': image_ids,
        })

    def prepare_image(self, connection, image_id):
        """
        Call the `prepare_image` method on the agent.
        """
        return self._command(connection, 'standby.prepare_image', {
            'task_id': self.new_task_id(),
            'image_id': image_id,
        })

    def run_image(self, connection, image_id):
        """
        Run the specified image.
        """
        return self._command(connection, 'standby.run_image', {
            'task_id': self.new_task_id(),
            'image_id': image_id,
        })
