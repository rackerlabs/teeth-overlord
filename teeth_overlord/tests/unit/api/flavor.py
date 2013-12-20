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


class TestFlavorAPI(tests.TeethAPITestCase):

    def setUp(self):
        super(TestFlavorAPI, self).setUp()

        self.url = '/v1.0/flavors'

        self.flavor_objects_mock = self.add_mock(models.Flavor)
        self.flavor1 = models.Flavor(id='flavor1',
                                     name='flavor1_name',
                                     deleted=False)
        self.flavor2 = models.Flavor(id='flavor2',
                                     name='flavor2_name',
                                     deleted=False)

    def test_list_flavors_some(self):
        self.list_some(models.Flavor,
                       self.flavor_objects_mock,
                       self.url,
                       [self.flavor1, self.flavor2])

    def test_list_flavors_none(self):
        self.list_none(models.Flavor,
                       self.flavor_objects_mock,
                       self.url,
                       [self.flavor1, self.flavor2])

    def test_fetch_flavors_one(self):
        self.fetch_one(models.Flavor,
                       self.flavor_objects_mock,
                       self.url,
                       [self.flavor1, self.flavor2])

    def test_fetch_flavors_none(self):
        self.fetch_none(models.Flavor,
                        self.flavor_objects_mock,
                        self.url,
                        [self.flavor1, self.flavor2])

    def test_delete_flavors_none(self):
        self.delete_none(models.Flavor,
                         self.flavor_objects_mock,
                         self.url,
                         [self.flavor1, self.flavor2])

    def test_create_flavors(self):

        response = self.make_request('POST', self.url,
                                     data={'name': 'created_flavor'})

        self.assertEqual(response.status_code, 201)

        # get the saved instance
        save_mock = self.get_mock(models.Flavor, 'save')
        self.assertEqual(save_mock.call_count, 1)
        flavor = save_mock.call_args[0][0]

        self.assertEqual(flavor.name, 'created_flavor')
        self.assertEqual(response.headers['Location'],
                         'http://localhost/v1.0/flavors/{id}'.format(
                             id=flavor.id))

    def test_create_flavor_missing_data(self):

        response = self.make_request('POST', self.url, {'foo': 'bar'})

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invalid request body')

    def test_delete_flavor(self):

        self.flavor_objects_mock.return_value = [self.flavor1]
        flavor_provider_mock = self.add_mock(models.FlavorProvider, return_value=[])

        response = self.make_request('DELETE', '{url}/{id}'.format(url=self.url,
                                                                   id=self.flavor1.id))

        self.assertEqual(response.status_code, 204)

        # get the saved instance
        save_mock = self.get_mock(models.Flavor, 'save')
        self.assertEqual(save_mock.call_count, 1)
        flavor = save_mock.call_args[0][0]

        flavor_provider_mock.assert_called_once_with('filter',
                                                     deleted=False,
                                                     flavor_id=self.flavor1.id)

        self.assertEqual(flavor.deleted, True)

    def test_delete_flavor_active_flavor_provider(self):
        self.flavor_objects_mock.return_value = [self.flavor1]
        flavor_provider_mock = self.add_mock(models.FlavorProvider,
                                             return_value=[models.FlavorProvider(flavor_id="fid",
                                                                                 chassis_model_id="cmid",
                                                                                 deleted=False)])

        response = self.make_request('DELETE', '{url}/{id}'.format(url=self.url,
                                                                   id=self.flavor1.id))

        self.assertEqual(response.status_code, 403)

        flavor_provider_mock.assert_called_once_with('filter',
                                                     deleted=False,
                                                     flavor_id=self.flavor1.id)

        # get the saved instance
        save_mock = self.get_mock(models.Flavor, 'save')
        self.assertEqual(save_mock.call_count, 0)

        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Object cannot be deleted')

    def test_delete_flavor_already_deleted(self):

        self.flavor1.deleted = True
        self.flavor_objects_mock.return_value = [self.flavor1]

        response = self.make_request('DELETE', '{url}/{id}'.format(url=self.url,
                                                                   id=self.flavor1.id))

        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Object already deleted')

        save_mock = self.get_mock(models.Flavor, 'save')
        self.assertEqual(save_mock.call_count, 0)
