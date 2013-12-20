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


class TestChassisModelAPI(tests.TeethAPITestCase):

    def setUp(self):
        super(TestChassisModelAPI, self).setUp()

        self.url = '/v1.0/chassis_models'

        self.chassis_model_objects_mock = self.add_mock(models.ChassisModel)
        self.chassismodel1 = models.ChassisModel(id='chassismodel1',
                                                 name='chassismodel1_name',
                                                 deleted=False)
        self.chassismodel2 = models.ChassisModel(id='chassismodel2',
                                                 name='chassismodel2_name',
                                                 deleted=False)

    def test_list_chassis_model_some(self):
        self.list_some(models.ChassisModel,
                       self.chassis_model_objects_mock,
                       self.url,
                       [self.chassismodel1, self.chassismodel2])

    def test_list_chassis_model_none(self):
        self.list_none(models.ChassisModel,
                       self.chassis_model_objects_mock,
                       self.url,
                       [self.chassismodel1, self.chassismodel2])

    def test_fetch_chassis_model_one(self):
        self.fetch_one(models.ChassisModel,
                       self.chassis_model_objects_mock,
                       self.url,
                       [self.chassismodel1, self.chassismodel2])

    def test_fetch_chassis_model_none(self):
        self.fetch_none(models.ChassisModel,
                        self.chassis_model_objects_mock,
                        self.url,
                        [self.chassismodel1, self.chassismodel2])

    def test_delete_chassis_model_none(self):
        self.delete_none(models.ChassisModel,
                         self.chassis_model_objects_mock,
                         self.url,
                         [self.chassismodel1, self.chassismodel2])

    def test_create_chassis_model(self):

        response = self.make_request('POST', self.url,
                                     data={'name': 'created_chassis_model'})

        self.assertEqual(response.status_code, 201)

        # get the saved instance
        save_mock = self.get_mock(models.ChassisModel, 'save')
        self.assertEqual(save_mock.call_count, 1)
        chassis_model = save_mock.call_args[0][0]

        self.assertEqual(chassis_model.name, 'created_chassis_model')
        self.assertEqual(response.headers['Location'],
                         'http://localhost{url}/{id}'.format(
                             url=self.url,
                             id=chassis_model.id))

    def test_create_chassis_model_missing_data(self):
        response = self.make_request('POST', self.url, {'foo': 'bar'})

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invalid request body')

    def test_delete_chassis_model(self):

        self.chassis_model_objects_mock.return_value = [self.chassismodel1]
        flavor_provider_mock = self.add_mock(
            models.FlavorProvider,
            return_value=[])

        response = self.make_request(
            'DELETE',
            '{url}/{id}'.format(url=self.url, id=self.chassismodel1.id))

        self.assertEqual(response.status_code, 204)

        # get the saved instance
        save_mock = self.get_mock(models.ChassisModel, 'save')
        self.assertEqual(save_mock.call_count, 1)
        chassis_model = save_mock.call_args[0][0]

        flavor_provider_mock.assert_called_once_with(
            'filter',
            deleted=False,
            chassis_model_id=self.chassismodel1.id)

        self.assertEqual(chassis_model.deleted, True)

    def test_delete_chassis_model_active_flavor_provider(self):
        self.chassis_model_objects_mock.return_value = [self.chassismodel1]
        flavor_provider_mock = self.add_mock(
            models.FlavorProvider,
            return_value=[models.FlavorProvider(flavor_id="fid",
                                                chassis_model_id="cmid",
                                                deleted=False)])

        response = self.make_request(
            'DELETE',
            '{url}/{id}'.format(url=self.url, id=self.chassismodel1.id))

        self.assertEqual(response.status_code, 403)

        # get the saved instance
        save_mock = self.get_mock(models.ChassisModel, 'save')
        self.assertEqual(save_mock.call_count, 0)

        flavor_provider_mock.assert_called_once_with(
            'filter',
            deleted=False,
            chassis_model_id=self.chassismodel1.id)

        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Object cannot be deleted')

    def test_delete_flavor_already_deleted(self):

        self.chassismodel1.deleted = True
        self.chassis_model_objects_mock.return_value = [self.chassismodel1]

        response = self.make_request(
            'DELETE',
            '{url}/{id}'.format(url=self.url, id=self.chassismodel1.id))

        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Object already deleted')

        save_mock = self.get_mock(models.ChassisModel, 'save')
        self.assertEqual(save_mock.call_count, 0)
