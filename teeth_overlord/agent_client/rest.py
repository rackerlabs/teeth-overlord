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
from teeth_rest import encoding

from teeth_overlord.agent_client import base
from teeth_overlord import errors
from teeth_overlord import models


class RESTAgentClient(base.BaseAgentClient):
    """Client for interacting with agents via a REST API."""
    def __init__(self, config):
        super(RESTAgentClient, self).__init__(config)
        view = encoding.SerializationViews.PUBLIC
        self.encoder = encoding.RESTJSONEncoder(view)
        self.session = requests.Session()

    def _get_command_url(self, agent):
        return '{}/v1/commands'.format(agent.url)

    def _get_command_body(self, method, params):
        return self.encoder.encode({
            'name': method,
            'params': params,
        })

    def _command(self, agent, method, params):
        url = self._get_command_url(agent)
        body = self._get_command_body(method, params)
        headers = {
            'Content-Type': 'application/json'
        }
        response = self.session.post(url, data=body, headers=headers)

        # TODO(russellhaering): real error handling
        return json.loads(response.text)

    def get_agent(self, chassis):
        """Retrieve an agent for the specified Chassis."""
        query = models.Agent.objects.filter(id=chassis.agent_id)

        try:
            return query.get()
        except models.Agent.DoesNotExist:
            raise errors.AgentNotConnectedError(chassis.id)

    def cache_image(self, agent, image_id):
        """Attempt to cache the specified image."""
        self.log.debug('Caching image {image} on agent {agent}.',
                       image=image_id,
                       agent=agent.url)
        return self._command(agent, 'standby.cache_image', {
            'task_id': self.new_task_id(),
            'image_id': image_id,
        })

    def prepare_image(self, agent, image_info, metadata, files):
        """Call the `prepare_image` method on the agent."""
        self.log.debug('Preparing image {image} on agent {agent}.',
                       image=image_info.get('image_id'),
                       agent=agent.url)
        return self._command(agent, 'standby.prepare_image', {
            'image_info': image_info,
            'metadata': metadata,
            'files': files,
            'task_id': self.new_task_id(),
        })

    def run_image(self, agent, image_id):
        """Run the specified image."""
        self.log.debug('Running image {image} on agent {agent}.',
                       image=image_id,
                       agent=agent.url)
        return self._command(agent, 'standby.run_image', {
            'task_id': self.new_task_id(),
            'image_id': image_id,
        })

    def secure_drives(self, agent, drives, key):
        """Secures given drives with given key."""
        self.log.info('Securing drives {drives} for agent {agent}',
                      drives=drives,
                      agent=agent.url)
        return self._command(agent, 'decom.secure_drives', {
            'drives': drives,
            'key': key,
        })

    def erase_drives(self, agent, drives, key):
        """Erases given drives."""
        self.log.info('Erasing drives {drives} for agent {agent}',
                      drives=drives,
                      agent=agent.url)
        return self._command(agent, 'decom.erase_drives', {
            'drives': drives,
            'key': key,
        })
