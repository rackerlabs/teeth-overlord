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
from teeth_overlord import tests


class TestChassisAPI(tests.TeethAPITestCase):

    def setUp(self):
        super(TestChassisAPI, self).setUp()

        self.url = '/v1/chassis'

        self.chassis_objects_mock = self.add_mock(models.Chassis)
        self.chassis1 = models.Chassis(id='chassis1',
                                       state=models.ChassisState.READY)
        self.chassis2 = models.Chassis(id='chassis2',
                                       state=models.ChassisState.BUILD,
                                       instance_id="instance_id")

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

    def test_delete_chassis_none(self):
        self.delete_none(models.Chassis,
                         self.chassis_objects_mock,
                         self.url,
                         [self.chassis1, self.chassis2])

    def test_create_chassis(self):
        return_value = [
            models.ChassisModel(id='chassis_model_id', name='chassis_model'),
        ]
        self.add_mock(models.ChassisModel, return_value=return_value)

        data = {
            'chassis_model_id': 'chassis_model_id',
        }
        response = self.make_request('POST', self.url, data=data)

        # get the saved instance
        chassis_save_mock = self.get_mock(models.Chassis, 'save')

        self.assertEqual(chassis_save_mock.call_count, 1)

        chassis = chassis_save_mock.call_args[0][0]

        self.assertEqual(chassis.chassis_model_id, 'chassis_model_id')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['Location'],
                         'http://localhost{url}/{id}'.format(url=self.url,
                                                             id=chassis.id))

    def test_create_chassis_deleted_chassis_model(self):
        self.add_mock(models.ChassisModel,
                      return_value=[models.ChassisModel(id='chassis_model_id',
                                                        name='chassis_model',
                                                        deleted=True)])

        response = self.make_request(
            'POST',
            self.url,
            data={'chassis_model_id': 'chassis_model_id'})

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid request body')
        self.assertTrue('ChassisModel is deleted' in data['details'])

    def test_create_chassis_bad_chassis_model(self):
        self.add_mock(models.ChassisModel,
                      side_effect=models.ChassisModel.DoesNotExist)

        data = {
            'chassis_model_id': 'does_not_exist',
        }
        response = self.make_request('POST', self.url, data=data)

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid request body')
        self.assertEqual(self.get_mock(models.Chassis, 'save').call_count, 0)

    def test_delete_chassis(self):
        self.chassis_objects_mock.return_value = [self.chassis1]

        response = self.make_request('DELETE',
                                     '{url}/{id}'.format(url=self.url,
                                                         id=self.chassis1.id))

        self.assertEqual(response.status_code, 204)

        save_mock = self.get_mock(models.Chassis, "save")
        self.assertEqual(save_mock.call_count, 1)
        chassis = save_mock.call_args[0][0]

        self.assertEqual(chassis.state, models.ChassisState.DELETED)

    def test_delete_chassis_already_deleted(self):
        self.chassis1.state = models.ChassisState.DELETED
        self.chassis_objects_mock.return_value = [self.chassis1]

        response = self.make_request('DELETE',
                                     '{url}/{id}'.format(url=self.url,
                                                         id=self.chassis1.id))

        self.assertEqual(response.status_code, 403)

        save_mock = self.get_mock(models.Chassis, "save")
        self.assertEqual(save_mock.call_count, 0)

        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Object already deleted')

    def test_delete_chassis_with_active_instance(self):
        self.chassis_objects_mock.return_value = [self.chassis2]

        response = self.make_request('DELETE',
                                     '{url}/{id}'.format(url=self.url,
                                                         id=self.chassis2.id))

        self.assertEqual(response.status_code, 403)

        save_mock = self.get_mock(models.Chassis, "save")
        self.assertEqual(save_mock.call_count, 0)

        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Object cannot be deleted')
