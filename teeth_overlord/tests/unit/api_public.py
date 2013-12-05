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

import unittest
import json

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import BaseRequest

from teeth_overlord.config import Config
from teeth_overlord.api.public import TeethPublicAPI, TeethPublicAPIServer


class TestPublicAPI(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.public_api = TeethPublicAPIServer(self.config)

    def build_request(self, method, path, data=None, query=None):
        if data:
            data = json.dumps(data)

        builder = EnvironBuilder(method=method, path=path, data=data,
                                 content_type='application/json', query_string=query)

        return builder.get_request(BaseRequest)

    def test_routes(self):
        public_api_component = self.public_api.components.get('/v1.0')
        self.assertIsInstance(public_api_component, TeethPublicAPI)

        expected_mappings = {
            # Chassis Models
            ('GET', '/v1.0/chassis_models'): (public_api_component.list_chassis_models, {}),
            ('GET', '/v1.0/chassis_models/foo-chassis-model'): (
                public_api_component.fetch_chassis_model,
                {
                    'chassis_model_id': 'foo-chassis-model',
                }
            ),
            ('POST', '/v1.0/chassis_models'): (public_api_component.create_chassis_model, {}),

            # Flavors
            ('GET', '/v1.0/flavors'): (public_api_component.list_flavors, {}),
            ('GET', '/v1.0/flavors/foo-flavor'): (public_api_component.fetch_flavor, {
                'flavor_id': 'foo-flavor',
            }),
            ('POST', '/v1.0/flavors'): (public_api_component.create_flavor, {}),

            # Flavor Providers
            ('GET', '/v1.0/flavor_providers'): (public_api_component.list_flavor_providers, {}),
            ('GET', '/v1.0/flavor_providers/foo-flavor-provider'): (
                public_api_component.fetch_flavor_provider,
                {
                    'flavor_provider_id': 'foo-flavor-provider',
                }
            ),
            ('POST', '/v1.0/flavor_providers'): (public_api_component.create_flavor_provider, {}),

            # Chassis
            ('GET', '/v1.0/chassis'): (public_api_component.list_chassis, {}),
            ('GET', '/v1.0/chassis/foo-chassis'): (public_api_component.fetch_chassis, {
                'chassis_id': 'foo-chassis',
            }),
            ('POST', '/v1.0/chassis'): (public_api_component.create_chassis, {}),

            # Instance
            ('GET', '/v1.0/instances'): (public_api_component.list_instances, {}),
            ('GET', '/v1.0/instances/foo-instance'): (public_api_component.fetch_instance, {
                'instance_id': 'foo-instance',
            }),
            ('POST', '/v1.0/instances'): (public_api_component.create_instance, {}),
        }

        for (method, path), (expected_endpoint, expected_values) in expected_mappings.iteritems():
            request = self.build_request(method, path)
            matched_endpoint, matched_values = self.public_api.match_request(request)
            self.assertEqual(matched_endpoint, expected_endpoint)
            self.assertEqual(matched_values, expected_values)
