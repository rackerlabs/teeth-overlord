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

import structlog

from teeth_overlord.networks import base

from keystoneclient.apiclient import exceptions as keystone_exceptions
from keystoneclient.v2_0 import client as keystone_client

from neutronclient.common import exceptions as neutron_exceptions
from neutronclient.neutron import client as neutron_client


def list_networks(client):
    try:
        netwrks = client.list_networks()['networks']
        netwrks = [NeutronNetworkInfo.deserialize(n, client) for n in netwrks]
        return netwrks
    except neutron_exceptions.NeutronException as e:
        raise NeutronProvider.NetworkProviderException(str(e))


def list_ports(mac_address, client):
    try:
        ports = client.list_ports(mac_address=mac_address)['ports']
        ports = [NeutronPortInfo.deserialize(p, client) for p in ports]
        return ports
    except neutron_exceptions.NeutronException as e:
        raise NeutronProvider.NetworkProviderException(str(e))


def get_network_info(network_id, client):
    try:
        network = client.show_network(network_id)['network']
        return NeutronNetworkInfo.deserialize(network, client)
    except neutron_exceptions.NeutronException as e:
        if '404 Not Found' in e.message:
            raise NeutronProvider.NetworkDoesNotExist(
                'Network with id {} does not exist'.format(network_id))
        else:
            raise NeutronProvider.NetworkProviderException(str(e))


def get_subnet_info(subnet_id, client):
    try:
        subnet = client.show_subnet(subnet_id)['subnet']
        return NeutronSubnetInfo.deserialize(subnet, client)
    except neutron_exceptions.NeutronException as e:
        if '404 Not Found' in e.message:
            raise NeutronProvider.SubnetDoesNotExist(
                'Subnet with id {} does not exist'.format(subnet_id))
        else:
            raise NeutronProvider.NetworkProviderException(str(e))


class NeutronSubnetInfo(base.SubnetInfo):

    @classmethod
    def deserialize(cls, body, client):
        d = {
            'id': body.get('id'),
            'name': body.get('name'),
            'ip_version': body.get('ip_version'),
            'gateway_ip': body.get('gateway_ip'),
            'cidr': body.get('cidr'),
            'enable_dhcp': body.get('enable_dhcp')
        }

        return cls(**d)


class NeutronNetworkInfo(base.NetworkInfo):

    @classmethod
    def deserialize(cls, body, client):
        d = {
            'id': body.get('id'),
            'name': body.get('name'),
            'status': body.get('status')
        }

        subnets = [get_subnet_info(s, client) for s in body.get('subnets')]
        d['subnets'] = [s.serialize() for s in subnets]

        return cls(**d)


class NeutronPortInfo(base.PortInfo):

    @classmethod
    def deserialize(cls, body, client):
        d = {
            'id': body.get('id'),
            'name': body.get('name'),
            'status': body.get('status'),
            'mac_address': body.get('mac_address'),
            'fixed_ips': body.get('fixed_ips')
        }

        n = get_network_info(body.get('network_id'), client)
        d['network'] = n.serialize()

        return cls(**d)


class NeutronProvider(base.BaseNetworkProvider):

    def __init__(self, config):
        super(NeutronProvider, self).__init__(config)
        self.log = structlog.get_logger()

    def _get_auth_token(self):
        try:
            auth = keystone_client.Client(
                username=self.config.KEYSTONE_USER,
                password=self.config.KEYSTONE_PASS,
                tenant_id=self.config.KEYSTONE_TENANT_ID,
                auth_url=self.config.KEYSTONE_AUTH_URL)
            return auth.auth_token
        except keystone_exceptions.ClientException as e:
            raise self.NetworkProviderException(
                'Cannot Initialize Keystone Client: {}'.format(str(e)))

    def _get_neutron_client(self):
        try:
            return neutron_client.Client(self.config.NEUTRON_VERSION,
                                         endpoint_url=self.config.NEUTRON_URL,
                                         token=self._get_auth_token())
        except neutron_exceptions.NeutronException as e:
            raise self.NetworkProviderException(
                'Cannot Initialize Neutron Client: {}'.format(str(e)))

    def attach(self, mac_address, network_id):
        """Attach a chassis to a given network_id."""
        client = self._get_neutron_client()

        p = {
            'network_id': network_id,
            'admin_state_up': True,
            'mac_address': mac_address
        }
        try:
            self.log.info('attaching port', **{'mac_address': mac_address,
                                               'network_id': network_id})
            port = client.create_port({'port': p})['port']
        except neutron_exceptions.NeutronException as e:
            self.log.error('failed attaching port', exc=str(e))
            raise self.NetworkProviderException(str(e))

        return NeutronPortInfo.deserialize(port, client)

    def detach(self, mac_address, network_id=None):
        """Detatch a mac_address from networks."""
        client = self._get_neutron_client()

        try:
            list_args = {'mac_address': mac_address}
            if network_id:
                list_args['network_id'] = network_id

            ports = client.list_ports(**list_args)['ports']

            for port in ports:
                self.log.info('detatching port',
                              **{'mac_address': port['mac_address'],
                                 'port_id': port['id'],
                                 'network_id': port['network_id']})
                client.delete_port(port['id'])

        except neutron_exceptions.NeutronException as e:
            self.log.error('failed detaching port', exc=str(e))
            raise self.NetworkProviderException(str(e))

    def list_ports(self, mac_address):
        client = self._get_neutron_client()
        return list_ports(mac_address, client)

    def get_network_info(self, network_id):
        client = self._get_neutron_client()
        network = get_network_info(network_id, client)
        return network

    def list_networks(self):
        client = self._get_neutron_client()
        return list_networks(client)

    def get_default_networks(self):
        return [self.config.NEUTRON_PUBLIC_NETWORK,
                self.config.NEUTRON_PRIVATE_NETWORK]

    def get_service_network(self):
        return self.config.NEUTRON_SERVICE_NETWORK
