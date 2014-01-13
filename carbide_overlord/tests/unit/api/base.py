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

from teeth_overlord.api import public

from teeth_overlord import models
from teeth_overlord import tests


class TestAPI(tests.TeethAPITestCase):

    def setUp(self):
        super(TestAPI, self).setUp()

        self.url = 'v1/instances'
        self.test_host = 'http://localhost/'

        self.instance1 = models.Instance(id='instance1',
                                         name='instance1_name',
                                         flavor_id='flavor1',
                                         image_id='image1',
                                         chassis_id='chassis1',
                                         state=models.InstanceState.ACTIVE)
        self.instance2 = models.Instance(id='instance2',
                                         name='instance2_name',
                                         flavor_id='flavor2',
                                         image_id='image2',
                                         chassis_id='chassis2',
                                         state=models.InstanceState.DELETED)

    def test_pagination_limit(self):

        instance_mock = self.add_mock(
            models.Instance,
            return_value=[self.instance1, self.instance2])

        query = {'limit': 1}
        response = self.make_request('GET',
                                     '/v1/instances',
                                     query=query)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(len(data['items']), 1)
        self.assertModelContains(data['items'][0], self.instance1)

        self.assertEqual(
            data['links'],
            [{'href': '{}{}?marker=instance1&limit=1'.format(self.test_host,
                                                             self.url),
              'rel': 'next'}])

        instance_mock.assert_called_with('limit', 1)
        instance_mock.assert_called_once('all')
        instance_mock.assert_not_called('filter')

    def test_pagination_marker(self):

        instance_mock = self.add_mock(
            models.Instance,
            return_value=[self.instance1, self.instance2])

        query = {'marker': self.instance1.id}
        response = self.make_request('GET',
                                     '/v1/instances',
                                     query=query)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(len(data['items']), 2)
        self.assertModelContains(data['items'][0], self.instance1)

        self.assertEqual(data['links'], [])

        instance_mock.assert_called_with('limit', public.DEFAULT_LIMIT)
        instance_mock.assert_called_once('all')

        instance_mock.assert_called_once('filter')
        filter_call_args = instance_mock.call_args('filter')[0][2]
        self.assertEqual(len(filter_call_args), 1)
        self.assertTrue('pk__token__gt' in filter_call_args)
        self.assertTrue(filter_call_args['pk__token__gt'], self.instance1.id)

    def test_mulitple_query_parameters(self):
        self.add_mock(models.Instance)

        response = self.make_request('GET',
                                     '/v1/instances?limit=1&limit=1')

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invalid query parameters')

    def test_invalid_limit(self):
        self.add_mock(models.Instance)

        query = {'limit': 0}
        response = self.make_request('GET',
                                     '/v1/instances',
                                     query=query)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invalid query parameters')

        query = {'limit': 'foobar'}
        response = self.make_request('GET',
                                     '/v1/instances',
                                     query=query)

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Invalid query parameters')

    def test_routes(self):
        public_api_component = self.api.components.get('/v1')
        self.assertIsInstance(public_api_component, public.TeethPublicAPI)

        expected_mappings = {
            # Chassis Models
            ('GET', '/v1/chassis_models'): (
                public_api_component.list_chassis_models,
                {},
            ),
            ('GET', '/v1/chassis_models/foo-chassis-model'): (
                public_api_component.fetch_chassis_model,
                {
                    'chassis_model_id': 'foo-chassis-model',
                },
            ),
            ('POST', '/v1/chassis_models'): (
                public_api_component.create_chassis_model,
                {},
            ),

            # Flavors
            ('GET', '/v1/flavors'): (public_api_component.list_flavors, {}),
            ('GET', '/v1/flavors/foo-flavor'): (
                public_api_component.fetch_flavor,
                {
                    'flavor_id': 'foo-flavor',
                },
            ),
            ('POST', '/v1/flavors'): (
                public_api_component.create_flavor,
                {},
            ),

            # Flavor Providers
            ('GET', '/v1/flavor_providers'): (
                public_api_component.list_flavor_providers,
                {},
            ),
            ('GET', '/v1/flavor_providers/foo-flavor-provider'): (
                public_api_component.fetch_flavor_provider,
                {
                    'flavor_provider_id': 'foo-flavor-provider',
                },
            ),
            ('POST', '/v1/flavor_providers'): (
                public_api_component.create_flavor_provider,
                {},
            ),

            # Chassis
            ('GET', '/v1/chassis'): (
                public_api_component.list_chassis,
                {},
            ),
            ('GET', '/v1/chassis/foo-chassis'): (
                public_api_component.fetch_chassis,
                {
                    'chassis_id': 'foo-chassis',
                },
            ),
            ('POST', '/v1/chassis'): (
                public_api_component.create_chassis,
                {},
            ),

            # Instance
            ('GET', '/v1/instances'): (
                public_api_component.list_instances,
                {},
            ),
            ('GET', '/v1/instances/foo-instance'): (
                public_api_component.fetch_instance,
                {
                    'instance_id': 'foo-instance',
                },
            ),
            ('POST', '/v1/instances'): (
                public_api_component.create_instance,
                {},
            ),
            ('DELETE', '/v1/instances/foo-instance'): (
                public_api_component.delete_instance,
                {
                    'instance_id': 'foo-instance',
                },
            ),
        }

        for key, value in expected_mappings.iteritems():
            method, path = key
            expected_endpoint, expected_values = value

            request = self.build_request(method, path)
            matched_endpoint, matched_values = self.api.match_request(
                request)
            self.assertEqual(matched_endpoint, expected_endpoint)
            self.assertEqual(matched_values, expected_values)
