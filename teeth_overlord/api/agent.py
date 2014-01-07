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

from teeth_rest import component
from teeth_rest import responses

from teeth_overlord import models
from teeth_overlord import stats


class TeethAgentAPI(component.APIComponent):

    """API for teeth agent process."""

    def __init__(self, config, stats_client=None):
        super(TeethAgentAPI, self).__init__()
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

        return responses.UpdatedResponse()


class TeethAgentAPIServer(component.APIServer):

    """Server for the teeth overlord API."""

    def __init__(self, config):
        super(TeethAgentAPIServer, self).__init__()
        self.config = config
        self.add_component('/v1.0', TeethAgentAPI(self.config))
