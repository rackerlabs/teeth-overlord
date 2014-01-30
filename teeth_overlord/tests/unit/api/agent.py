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

        self.url = '/v1/agents'
        self.agent_model_mock = self.add_mock(models.Agent)

        self.chassis = models.Chassis(id='chassis_id')
        self.chassis_mock = self.add_mock(models.Chassis)
        self.chassis_mock.return_value = [self.chassis]

        self.h2c = models.HardwareToChassis(chassis_id='chassis_id',
                                            hardware_type='mac_address',
                                            hardware_id='0:1:2:3:4:5')
        self.h2c_mock = self.add_mock(models.HardwareToChassis)
        self.h2c_mock.return_value = [self.h2c]

    @mock.patch('time.time', mock.MagicMock(return_value=0))
    def test_update_agent(self):
        data = {
            'version': '0.1',
            'mode': models.AgentState.STANDBY,
            'hardware': [
                {'type': 'mac_address', 'id': '0:1:2:3:4:5'},
            ]
        }
        return_value = [models.Agent(**data)]
        self.agent_model_mock.return_value = return_value

        response = self.make_request('PUT', self.url, data=data)

        save_mock = self.get_mock(models.Agent, 'save')
        self.assertEqual(save_mock.call_count, 1)
        agent = save_mock.call_args[0][0]

        self.assertEqual(agent.version, '0.1')
        self.assertEqual(agent.url, 'http://127.0.0.1:9999')
        self.assertEqual(agent.mode, models.AgentState.STANDBY)

        self.assertEqual(response.status_code, 204)
        heartbeat_before = response.headers['Heartbeat-Before']
        self.assertEqual(heartbeat_before, str(models.Agent.TTL))
