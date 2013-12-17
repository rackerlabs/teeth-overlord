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


class TestChassisModelAPI(TeethUnitTest):

    def setUp(self):
        super(TestChassisModelAPI, self).setUp()

        self.url = '/v1.0/chassis_models'

        self.chassis_model_objects_mock = self.add_mock(models.ChassisModel)
        self.chassismodel1 = models.ChassisModel(id='chassismodel1',
                                                 name='chassismodel1_name')
        self.chassismodel2 = models.ChassisModel(id='chassismodel2',
                                                 name='chassismodel2_name')

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

    def test_create_chassis_model(self):

        response = self.make_request('POST', self.url,
                                     data={'name': 'created_chassis_model'})

        self.assertEqual(response.status_code, 201)

        # get the saved instance
        saved = self.db_ops_mock.saved()
        self.assertEqual(len(saved), 1)
        chassis_model = saved[0]

        self.assertEqual(chassis_model.name, 'created_chassis_model')
        self.assertEqual(response.headers['Location'],
                         'http://localhost{url}/{id}'.format(url=self.url, id=chassis_model.id))

    def test_create_chassis_model_missing_data(self):

        response = self.make_request('POST', self.url, {'foo': 'bar'})

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data, {u'message': u'Invalid query parameters',
                                u'code': 400,
                                u'type': u'InvalidParametersError',
                                u'details': u'name - None values are not allowed'})
