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

from carbide_rest import component
from carbide_rest import responses

from carbide_overlord import models
from carbide_overlord import stats


class CarbideAgentAPI(component.APIComponent):

    """API for carbide agent process."""

    def __init__(self, config, stats_client=None):
        super(CarbideAgentAPI, self).__init__()
        self.config = config
        self.stats_client = stats_client or stats.get_stats_client(
            config,
            prefix='agent_api')

    def add_routes(self):
        """Called during initialization. Override to map relative routes to
        methods.
        """
        # Agent Handlers
        self.route('PUT', '/agents/<string:mac_address>', self.update_agent)

    @stats.incr_stat('agents.update')
    def update_agent(self, request, mac_address):
        """Creates or updates an agent with provided data."""
        data = self.parse_content(request)

        agent = models.Agent(primary_mac_address=mac_address)
        agent.version = data.get('version')
        agent.url = data.get('url')
        agent.mode = data.get('mode')
        agent.ttl(models.Agent.TTL)
        agent.save()

        expiry = time.time() + models.Agent.TTL
        headers = {'Heartbeat-Before': expiry}
        return responses.UpdatedResponse(headers=headers)


class CarbideAgentAPIServer(component.APIServer):

    """Server for the carbide overlord API."""

    def __init__(self, config):
        super(CarbideAgentAPIServer, self).__init__()
        self.config = config
        self.add_component('/v1', CarbideAgentAPI(self.config))
