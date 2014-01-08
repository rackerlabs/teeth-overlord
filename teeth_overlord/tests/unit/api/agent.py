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

import mock

from teeth_overlord.api import agent as agent_api
from teeth_overlord import models
from teeth_overlord import tests


class TestAgentAPI(tests.TeethAPITestCase):

    def setUp(self):
        super(TestAgentAPI, self).setUp()
        self.api = agent_api.TeethAgentAPIServer(self.config)

        self.url = '/v1/agents/00:00:00:00:00:00'
        self.agent_model_mock = self.add_mock(models.Agent)

    @mock.patch('time.time', mock.MagicMock(return_value=0))
    def test_update_agent(self):
        data = {
            'primary_mac_address': '00:00:00:00:00:00',
            'version': '0.1',
            'url': 'http://10.0.1.1:51200',
            'mode': models.AgentState.STANDBY,
        }
        return_value = [models.Agent(**data)]
        self.agent_model_mock.return_value = return_value

        response = self.make_request('PUT', self.url, data=data)

        save_mock = self.get_mock(models.Agent, 'save')
        self.assertEqual(save_mock.call_count, 1)
        agent = save_mock.call_args[0][0]

        self.assertEqual(agent.primary_mac_address, '00:00:00:00:00:00')
        self.assertEqual(agent.version, '0.1')
        self.assertEqual(agent.url, 'http://10.0.1.1:51200')
        self.assertEqual(agent.mode, models.AgentState.STANDBY)

        self.assertEqual(response.status_code, 204)
        heartbeat_before = response.headers['Heartbeat-Before']
        self.assertEqual(heartbeat_before, str(models.Agent.TTL))
