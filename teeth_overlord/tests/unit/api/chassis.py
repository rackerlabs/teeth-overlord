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

from teeth_overlord import models
from teeth_overlord.tests import TeethUnitTest


class TestChassisAPI(TeethUnitTest):

    def setUp(self):
        super(TestChassisAPI, self).setUp()

        self.url = '/v1.0/chassis'

        self.chassis_objects_mock = self.add_mock(models.Chassis)
        self.chassis1 = models.Chassis(id='chassis1',
                                       state=models.ChassisState.READY,
                                       primary_mac_address='1:2:3:4:5')
        self.chassis2 = models.Chassis(id='chassis2',
                                       state=models.ChassisState.BUILD,
                                       primary_mac_address='6:7:8:9:0')

    def test_list_chassis_some(self):
        self.list_some(models.Chassis,
                       self.chassis_objects_mock,
                       self.url,
                       [self.chassis1, self.chassis2])

    def test_list_chassis_none(self):
        self.list_none(models.Chassis,
                       self.chassis_objects_mock,
                       self.url,
                       [self.chassis1, self.chassis2])

    def test_fetch_chassis_one(self):
        self.fetch_one(models.Chassis,
                       self.chassis_objects_mock,
                       self.url,
                       [self.chassis1, self.chassis2])

    def test_fetch_chassis_none(self):
        self.fetch_none(models.Chassis,
                        self.chassis_objects_mock,
                        self.url,
                        [self.chassis1, self.chassis2])

    def test_create_chassis(self):
        self.add_mock(models.ChassisModel, return_value=[models.ChassisModel(id='chassis_model_id',
                                                                             name='chassis_model')])

        response = self.make_request('POST', self.url,
                                     data={'chassis_model_id': 'chassis_model_id',
                                           'primary_mac_address': 'mac_addr'})

        # get the saved instance
        saved = self.db_ops_mock.saved()
        self.assertEqual(len(saved), 1)
        chassis = saved[0]

        self.assertEqual(chassis.chassis_model_id, 'chassis_model_id')
        self.assertEqual(chassis.primary_mac_address, 'mac_addr')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['Location'],
                         'http://localhost{url}/{id}'.format(url=self.url, id=chassis.id))

    def test_create_flavor_provider_missing_data(self):
        response = self.make_request('POST', self.url,
                                     data={'chassis_model_id': 'chassis_model_id'})

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid query parameters')

    def test_create_instance_bad_chassis_model(self):
        self.add_mock(models.ChassisModel, side_effect=models.ChassisModel.DoesNotExist)

        response = self.make_request('POST', self.url,
                                     data={'chassis_model_id': 'does_not_exist',
                                           'primary_mac_address': 'mac_addr'})

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid request body')
        self.get_mock(models.Chassis, 'save').assert_not_called()
