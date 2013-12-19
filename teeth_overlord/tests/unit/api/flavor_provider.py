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


class TestFlavorProviderAPI(tests.TeethAPITestCase):

    def setUp(self):
        super(TestFlavorProviderAPI, self).setUp()

        self.url = '/v1.0/flavor_providers'

        self.flavor_provider_objects_mock = self.add_mock(models.FlavorProvider)
        self.flavorprovider1 = models.FlavorProvider(id='flavorprovider1',
                                                     flavor_id='flavor_id',
                                                     chassis_model_id='chassis_model_id',
                                                     schedule_priority=100)
        self.flavorprovider2 = models.FlavorProvider(id='flavorprovider2',
                                                     flavor_id='flavor_id',
                                                     chassis_model_id='chassis_model_id',
                                                     schedule_priority=50)

    def test_list_flavor_providers_some(self):
        self.list_some(models.FlavorProvider,
                       self.flavor_provider_objects_mock,
                       self.url,
                       [self.flavorprovider1, self.flavorprovider2])

    def test_list_flavor_providers_none(self):
        self.list_none(models.FlavorProvider,
                       self.flavor_provider_objects_mock,
                       self.url,
                       [self.flavorprovider1, self.flavorprovider2])

    def test_fetch_flavor_providers_one(self):
        self.fetch_one(models.FlavorProvider,
                       self.flavor_provider_objects_mock,
                       self.url,
                       [self.flavorprovider1, self.flavorprovider2])

    def test_fetch_flavor_providers_none(self):
        self.fetch_none(models.FlavorProvider,
                        self.flavor_provider_objects_mock,
                        self.url,
                        [self.flavorprovider1, self.flavorprovider2])

    def test_create_flavor_provider(self):
        self.add_mock(models.Flavor, return_value=[models.Flavor(id='flavor_id',
                                                                 name='some_flavor')])
        self.add_mock(models.ChassisModel, return_value=[models.ChassisModel(id='chassis_model_id',
                                                                             name='chassis_model')])

        response = self.make_request('POST', self.url,
                                     data={'flavor_id': 'flavor_id',
                                           'chassis_model_id': 'chassis_model_id',
                                           'schedule_priority': 100})

        # get the saved instance
        save_mock = self.get_mock(models.FlavorProvider, 'save')
        self.assertEqual(save_mock.call_count, 1)
        flavor_provider = save_mock.call_args[0][0]

        self.assertEqual(flavor_provider.chassis_model_id, 'chassis_model_id')
        self.assertEqual(flavor_provider.flavor_id, 'flavor_id')
        self.assertEqual(flavor_provider.schedule_priority, 100)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['Location'],
                         'http://localhost{url}/{id}'.format(url=self.url, id=flavor_provider.id))

    def test_create_flavor_provider_missing_data(self):
        response = self.make_request('POST', self.url,
                                     data={'flavor_id': 'flavor_id',
                                           'chassis_model_id': 'chassis_model_id'})

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid request body')

    def test_create_flavor_provider_bad_flavor(self):
        self.add_mock(models.Flavor, side_effect=models.Flavor.DoesNotExist)
        self.add_mock(models.ChassisModel, return_value=[models.ChassisModel(id='chassis_model_id',
                                                                             name='chassis_model')])

        response = self.make_request('POST', self.url,
                                     data={'flavor_id': 'does_not_exist',
                                           'chassis_model_id': 'chassis_model_id',
                                           'schedule_priority': 100})

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid request body')
        self.assertEqual(self.get_mock(models.FlavorProvider, 'save').call_count, 0)

    def test_create_flavor_provider_bad_chassis_model(self):
        self.add_mock(models.Flavor, return_value=[models.Flavor(id='flavor_id',
                                                                 name='some_flavor')])
        self.add_mock(models.ChassisModel, side_effect=models.ChassisModel.DoesNotExist)

        response = self.make_request('POST', self.url,
                                     data={'flavor_id': 'flavor_id',
                                           'chassis_model_id': 'does_not_exist',
                                           'schedule_priority': 100})

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid request body')
        self.assertEqual(self.get_mock(models.FlavorProvider, 'save').call_count, 0)
