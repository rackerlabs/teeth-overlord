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

import collections

from teeth_overlord import config
from teeth_overlord.networks import neutron
from teeth_overlord import tests

from keystoneclient.apiclient import exceptions as keystone_exceptions
from keystoneclient.v2_0 import client as keystone_client

from neutronclient.common import exceptions as neutron_exceptions
from neutronclient.neutron import client as neutron_client


NETWORK1_RESPONSE = {
    u'status': u'ACTIVE',
    u'subnets': [u'SUBNET1'],
    u'name': u'private',
    u'provider:physical_network': None,
    u'admin_state_up': True,
    u'tenant_id': u'TENANTID',
    u'provider:network_type': u'local',
    u'router:external': False,
    u'shared': False,
    u'id': u'NETWORK1',
    u'provider:segmentation_id': None
}

NETWORK2_RESPONSE = {
    u'status': u'ACTIVE',
    u'subnets': [u'SUBNET2'],
    u'name': u'public',
    u'provider:physical_network': None,
    u'admin_state_up': True,
    u'tenant_id': u'TENANTID',
    u'provider:network_type': u'local',
    u'router:external': True,
    u'shared': False,
    u'id': u'NETWORK2',
    u'provider:segmentation_id': None
}

PORT1_RESPONSE = {
    u'status': u'ACTIVE',
    u'binding:host_id': u'precise64',
    u'name': u'',
    u'allowed_address_pairs': [],
    u'admin_state_up': True,
    u'network_id': u'NETWORK1',
    u'tenant_id': u'TENANTID',
    u'extra_dhcp_opts': [],
    u'binding:vif_type': u'ovs',
    u'device_owner': u'network:dhcp',
    u'binding:capabilities': {u'port_filter': True},
    u'mac_address': u'fa:16:3e:e0:d4:63',
    u'fixed_ips': [
        {
            u'subnet_id': u'SUBNET1',
            u'ip_address': u'10.0.0.3'
        }
    ],
    u'id': u'PORT1',
    u'security_groups': [],
    u'device_id': u''
}

PORT2_RESPONSE = {
    u'status': u'DOWN',
    u'binding:host_id': u'',
    u'name': u'',
    u'allowed_address_pairs': [],
    u'admin_state_up': True,
    u'network_id': u'NETWORK2',
    u'tenant_id': u'TENANTID',
    u'extra_dhcp_opts': [],
    u'binding:vif_type': u'unbound',
    u'device_owner': u'',
    u'binding:capabilities': {u'port_filter': False},
    u'mac_address': u'00:09:7b:3e:18:ca',
    u'fixed_ips': [
        {
            u'subnet_id': u'SUBNET2',
            u'ip_address': u'192.168.27.3'
        }
    ],
    u'id': u'PORT2',
    u'security_groups': [u'SECGRP'],
    u'device_id': u''
}

SUBNET1_RESPONSE = {
    u'name': u'private-subnet',
    u'enable_dhcp': True,
    u'network_id': u'NETWORK1',
    u'tenant_id': u'TENANTID',
    u'dns_nameservers': [],
    u'allocation_pools': [
        {
            u'start': u'10.0.0.2',
            u'end': u'10.0.0.254'
        }
    ],
    u'host_routes': [],
    u'ip_version': 4,
    u'gateway_ip': u'10.0.0.1',
    u'cidr': u'10.0.0.0/24',
    u'id': u'SUBNET1'
}

SUBNET2_RESPONSE = {
    u'name': u'public-subnet',
    u'enable_dhcp': False,
    u'network_id': u'NETWORK2',
    u'tenant_id': u'TENANTID',
    u'dns_nameservers': [],
    u'allocation_pools': [
        {
            u'start': u'192.168.27.1',
            u'end': u'192.168.27.1'
        },
        {
            u'start': u'192.168.27.3',
            u'end': u'192.168.27.254'
        }
    ],
    u'host_routes': [],
    u'ip_version': 4,
    u'gateway_ip': u'192.168.27.2',
    u'cidr': u'192.168.27.0/24',
    u'id': u'SUBNET2'
}

SERIALIZED_NETWORK1 = collections.OrderedDict([
    ('id', u'NETWORK1'),
    ('name', u'private'),
    ('status', u'ACTIVE'),
    ('subnets', [
        collections.OrderedDict([
            ('id', u'SUBNET1'),
            ('name', u'private-subnet'),
            ('ip_version', 4),
            ('gateway_ip', u'10.0.0.1'),
            ('cidr', u'10.0.0.0/24'),
            ('enable_dhcp', True)
        ])
    ])
])

SERIALIZED_NETWORK2 = collections.OrderedDict([
    ('id', u'NETWORK2'),
    ('name', u'public'),
    ('status', u'ACTIVE'),
    ('subnets', [
        collections.OrderedDict([
            ('id', u'SUBNET2'),
            ('name', u'public-subnet'),
            ('ip_version', 4),
            ('gateway_ip', u'192.168.27.2'),
            ('cidr', u'192.168.27.0/24'),
            ('enable_dhcp', False)
        ])
    ])
])

SERIALIZED_PORT1 = collections.OrderedDict([
    ('id', u'PORT1'),
    ('name', u''),
    ('status', u'ACTIVE'),
    ('mac_address', u'fa:16:3e:e0:d4:63'),
    ('fixed_ips', [
        {
            u'subnet_id': u'SUBNET1',
            u'ip_address': u'10.0.0.3'
        }
    ]),
    ('network', SERIALIZED_NETWORK1)
])


class TestNeutronProvider(tests.TeethMockTestUtilities):

    def setUp(self):
        super(TestNeutronProvider, self).setUp()

        self.config = config.LazyConfig(config={
            'KEYSTONE_USER': 'user',
            'KEYSTONE_PASS': 'pass',
            'KEYSTONE_TENANT_ID': 'tenant',
            'KEYSTONE_AUTH_URL': 'auth_url',
            'NEUTRON_VERSION': '2.0',
            'NEUTRON_URL': 'neutron_url',
            'NEUTRON_PUBLIC_NETWORK': 'd6b32008-1432-4299-81c7-cbe3128ba13f',
            'NEUTRON_PRIVATE_NETWORK': '2afa16d6-7b84-484f-a642-af243b0e5b10',
            'NEUTRON_SERVICE_NETWORK': '2afa16d6-7b84-484f-a642-af243b0e5b10',
        })

        self.neutron_client_mock = self.add_mock(neutron_client, 'Client')
        self.neutron_mock = self.neutron_client_mock.return_value

        self.keystone_client_mock = self.add_mock(keystone_client, 'Client')
        self.keystone_client_mock.return_value.auth_token = 'auth_token'

        self.provider = neutron.NeutronProvider(self.config)

    def test_get_auth_token(self):

        t = self.provider._get_auth_token()

        self.assertEqual(t, 'auth_token')
        self.keystone_client_mock.assert_called_with(
            username='user',
            password='pass',
            tenant_id='tenant',
            auth_url='auth_url'
        )

    def test_get_auth_token_client_exception(self):
        exc = keystone_exceptions.ClientException
        self.keystone_client_mock.side_effect = exc

        self.assertRaises(self.provider.NetworkProviderException,
                          self.provider._get_auth_token)

    def test_get_neutron_client(self):

        self.provider._get_neutron_client()
        self.neutron_client_mock.assert_called_with(
            '2.0',
            endpoint_url='neutron_url',
            token='auth_token'
        )

    def test_get_neutron_client_exception(self):
        exc = neutron_exceptions.NeutronException()
        self.neutron_client_mock.side_effect = exc

        self.assertRaises(self.provider.NetworkProviderException,
                          self.provider._get_neutron_client)

    def test_list_networks(self):
        networks = {'networks': [NETWORK1_RESPONSE,
                                 NETWORK2_RESPONSE]}
        self.neutron_mock.list_networks.return_value = networks
        self.neutron_mock.show_subnet.side_effect = [
            {'subnet': SUBNET1_RESPONSE},
            {'subnet': SUBNET2_RESPONSE}
        ]

        networks = self.provider.list_networks()

        results = [
            SERIALIZED_NETWORK1,
            SERIALIZED_NETWORK2
        ]

        self.assertEqual([n.serialize() for n in networks], results)

    def test_list_networks_empty(self):
        self.neutron_mock.list_networks.return_value = {'networks': []}

        networks = self.provider.list_networks()

        self.neutron_mock.list_networks.assert_called()
        self.assertEqual(networks, [])

    def test_list_networks_client_exception(self):
        exc = neutron_exceptions.NeutronException()
        self.neutron_mock.list_networks.side_effect = exc

        self.assertRaises(self.provider.NetworkProviderException,
                          self.provider.list_networks)

    def test_get_network_info(self):
        network = {'network': NETWORK1_RESPONSE}
        self.neutron_mock.show_network.return_value = network
        self.neutron_mock.show_subnet.side_effect = [
            {'subnet': SUBNET1_RESPONSE}
        ]

        network = self.provider.get_network_info('NETWORK1')

        self.assertEqual(network.serialize(), SERIALIZED_NETWORK1)
        self.neutron_mock.show_network.assert_called_with('NETWORK1')

    def test_get_network_info_does_not_exist(self):
        exc = neutron_exceptions.NeutronException()
        exc.message = '404 Not Found'
        self.neutron_mock.show_network.side_effect = exc

        self.assertRaises(self.provider.NetworkDoesNotExist,
                          self.provider.get_network_info,
                          'NETWORK1')

    def test_get_network_info_client_exception(self):
        exc = neutron_exceptions.NeutronException()
        self.neutron_mock.show_network.side_effect = exc

        self.assertRaises(self.provider.NetworkProviderException,
                          self.provider.get_network_info,
                          'NETWORK1')

    def test_list_ports(self):
        ports = {'ports': [PORT1_RESPONSE]}
        self.neutron_mock.list_ports.return_value = ports
        network = {'network': NETWORK1_RESPONSE}
        self.neutron_mock.show_network.return_value = network
        subnet = {'subnet': SUBNET1_RESPONSE}
        self.neutron_mock.show_subnet.return_value = subnet

        ports = self.provider.list_ports('a:b:c:d')

        self.assertEqual([p.serialize() for p in ports], [SERIALIZED_PORT1])
        self.neutron_mock.list_ports.assert_called_with(mac_address='a:b:c:d')

    def test_attach(self):
        port = {'port': PORT1_RESPONSE}
        self.neutron_mock.create_port.return_value = port
        network = {'network': NETWORK1_RESPONSE}
        self.neutron_mock.show_network.return_value = network
        subnet = {'subnet': SUBNET1_RESPONSE}
        self.neutron_mock.show_subnet.return_value = subnet

        port = self.provider.attach('a:b:c:d', 'network_id')

        self.neutron_mock.create_port.assert_called_with({
            'port': {
                'network_id': 'network_id',
                'admin_state_up': True,
                'mac_address': 'a:b:c:d'
            }
        })
        self.assertEqual(port.serialize(), SERIALIZED_PORT1)

    def test_attach_client_exception(self):
        exc = neutron_exceptions.NeutronException()
        self.neutron_mock.create_port.side_effect = exc

        self.assertRaises(self.provider.NetworkProviderException,
                          self.provider.attach,
                          'mac_address', 'network_id')

    def test_detatch(self):
        ports = {'ports': [PORT1_RESPONSE]}
        self.neutron_mock.list_ports.return_value = ports
        network = {'network': NETWORK1_RESPONSE}
        self.neutron_mock.show_network.return_value = network
        subnet = {'subnet': SUBNET1_RESPONSE}
        self.neutron_mock.show_subnet.return_value = subnet

        self.provider.detach('a:b:c:d')

        self.neutron_mock.delete_port.assert_called_with(PORT1_RESPONSE['id'])
        self.neutron_mock.list_ports.assert_called_with(mac_address='a:b:c:d')

    def test_detach_specific_network(self):
        ports = {'ports': [PORT1_RESPONSE]}
        self.neutron_mock.list_ports.return_value = ports
        network = {'network': NETWORK1_RESPONSE}
        self.neutron_mock.show_network.return_value = network
        subnet = {'subnet': SUBNET1_RESPONSE}
        self.neutron_mock.show_subnet.return_value = subnet

        self.provider.detach('a:b:c:d', 'network_id')

        self.neutron_mock.delete_port.assert_called_with(PORT1_RESPONSE['id'])
        self.neutron_mock.list_ports.assert_called_with(
            mac_address='a:b:c:d', network_id='network_id')

    def test_detach_client_exception(self):
        ports = {'ports': [PORT1_RESPONSE]}
        self.neutron_mock.list_ports.return_value = ports
        network = {'network': NETWORK1_RESPONSE}
        self.neutron_mock.show_network.return_value = network
        subnet = {'subnet': SUBNET1_RESPONSE}
        self.neutron_mock.show_subnet.return_value = subnet
        exc = neutron_exceptions.NeutronException()
        self.neutron_mock.delete_port.side_effect = exc

        self.assertRaises(self.provider.NetworkProviderException,
                          self.provider.detach,
                          'a:b:c:d')

    def test_get_default_networks(self):

        network_ids = self.provider.get_default_networks()

        self.assertEqual(network_ids, [self.config.NEUTRON_PUBLIC_NETWORK,
                                       self.config.NEUTRON_PRIVATE_NETWORK])

    def test_get_service_network(self):

        network_id = self.provider.get_service_network()

        self.assertEqual(network_id, self.config.NEUTRON_SERVICE_NETWORK)
