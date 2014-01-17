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
import mock
import requests

from teeth_overlord.agent_client import rest as agent_client
from teeth_overlord import errors
from teeth_overlord import models
from teeth_overlord import tests


class MockResponse(object):
    def __init__(self, data):
        self.text = json.dumps(data)


class TestRESTAgentClient(tests.TeethMockTestUtilities):
    def setUp(self):
        super(TestRESTAgentClient, self).setUp()
        self.client = agent_client.RESTAgentClient(tests.TEST_CONFIG)
        self.client.session = mock.Mock(autospec=requests.Session)
        self.agent = models.Agent(primary_mac_address='a:b:c:d',
                                  version='8',
                                  url='http://10.0.1.1:51200',
                                  mode='STANDBY')
        self.agent_mock = self._mock_model(models.Agent,
                                           return_value=[self.agent])
        self.chassis = models.Chassis(id='test_chassis',
                                      chassis_model_id='chassis_model',
                                      primary_mac_address='a:b:c:d')

    def test_get_command_url(self):
        url = self.client._get_command_url(self.agent)
        self.assertEqual(url, 'http://10.0.1.1:51200/v1/commands')

    def test_get_agent(self):
        agent = self.client.get_agent(self.chassis)
        self.assertEqual(agent, self.agent)

    def test_agent_not_found_raises_error(self):
        self.agent_mock.side_effect = models.Agent.DoesNotExist
        self.assertRaises(errors.AgentNotConnectedError,
                          self.client.get_agent,
                          self.chassis)

    @mock.patch('uuid.uuid4', mock.MagicMock(return_value='uuid'))
    def test_cache_images(self):
        _command = self._mock_attr(self.client, '_command')
        image_ids = ['test_image', 'test_image_2']
        params = {'task_id': 'uuid', 'image_ids': image_ids}

        self.client.cache_images(self.agent, image_ids)
        _command.assert_called_once_with(self.agent,
                                         'cache_images',
                                         params)

    @mock.patch('uuid.uuid4', mock.MagicMock(return_value='uuid'))
    def test_prepare_image(self):
        _command = self._mock_attr(self.client, '_command')
        image_info = {}
        configdrive = {}
        device = '/dev/sda'
        params = {
            'task_id': 'uuid',
            'image_info': image_info,
            'configdrive': configdrive,
            'device': device,
        }

        self.client.prepare_image(self.agent, image_info, configdrive, device)
        _command.assert_called_once_with(self.agent,
                                         'prepare_image',
                                         params)

    @mock.patch('uuid.uuid4', mock.MagicMock(return_value='uuid'))
    def test_run_image(self):
        _command = self._mock_attr(self.client, '_command')
        image_id = 'test_image'
        params = {'task_id': 'uuid', 'image_id': image_id}

        self.client.run_image(self.agent, image_id)
        _command.assert_called_once_with(self.agent,
                                         'run_image',
                                         params)

    def test_command(self):
        response_data = {'status': 'ok'}
        self.client.session.post.return_value = MockResponse(response_data)
        method = 'run_image'
        params = {'task_id': 'uuid', 'image_id': 'test_image'}

        url = self.client._get_command_url(self.agent)
        body = self.client._get_command_body(method, params)
        headers = {'Content-Type': 'application/json'}

        response = self.client._command(self.agent, method, params)
        self.assertEqual(response, response_data)
        self.client.session.post.assert_called_once_with(url,
                                                         data=body,
                                                         headers=headers)
