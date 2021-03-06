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

import time
import uuid

import cqlengine

from teeth_rest import component
from teeth_rest import responses

from teeth_overlord import models
from teeth_overlord import stats

from teeth_overlord.networks import base as networks_base


DEFAULT_LIMIT = 100


class TeethAgentAPI(component.APIComponent):

    """API for teeth agent process."""

    def __init__(self, config, stats_client=None):
        super(TeethAgentAPI, self).__init__()
        self.config = config
        self.stats_client = stats_client or stats.get_stats_client(
            config,
            prefix='agent_api')
        self.network_provider = networks_base.get_network_provider(config)

    def add_routes(self):
        """Called during initialization. Override to map relative routes to
        methods.
        """
        # Agent Handlers
        self.route('PUT', '/agents', self.update_agent)

    @stats.incr_stat('agents.update')
    def update_agent(self, request):
        """Creates or updates an agent with provided data."""
        data = self.parse_content(request)

        forwarded_ip = request.headers.get('X-Forwarded-For')
        agent_ip = forwarded_ip or request.remote_addr
        url = '{}://{}:{}'.format(self.config.AGENT_PROTOCOL,
                                  agent_ip,
                                  self.config.AGENT_PORT)

        chassis = models.Chassis.find_by_hardware(data['hardware'])

        agent_id = str(uuid.uuid4())
        agent = models.Agent(id=agent_id)
        agent.version = data.get('version')
        agent.url = url
        # TODO(jimrollenhagen) do we still want this?
        agent.mode = data.get('mode')
        agent.ttl(models.Agent.TTL)

        chassis.agent_id = agent_id

        batch = cqlengine.BatchQuery()
        chassis.batch(batch).save()
        agent.batch(batch).save()
        batch.execute()

        expiry = time.time() + models.Agent.TTL
        headers = {'Heartbeat-Before': expiry}
        return responses.UpdatedResponse(headers=headers)


class TeethAgentAPIServer(component.APIServer):

    """Server for the teeth overlord API."""

    def __init__(self, config):
        super(TeethAgentAPIServer, self).__init__()
        self.config = config
        self.add_component('/v1', TeethAgentAPI(self.config))
