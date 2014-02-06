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


FAKE_SUBNETS = {
    'PUBLIC_SUBNET': base.SubnetInfo(
        id='PUBLIC_SUBNET',
        name='PUBLIC_SUBNET',
        ip_version=4,
        gateway_ip='10.0.0.1',
        cidr='10.0.0.0/24',
        enable_dhcp=False
    ),

    'PRIVATE_SUBNET': base.SubnetInfo(
        id='PRIVATE_SUBNET',
        name='PRIVATE_SUBNET',
        ip_version=4,
        gateway_ip='192.168.0.1',
        cidr='192.168.0.0/24',
        enable_dhcp=False
    ),

    'SERVICE_SUBNET': base.SubnetInfo(
        id='SERVICE_SUBNET',
        name='SERVICE_SUBNET',
        ip_version=4,
        gateway_ip='192.168.1.1',
        cidr='192.168.1.0/24',
        enable_dhcp=False
    )
}

FAKE_NETWORKS = {
    'PUBLIC_NETWORK': base.NetworkInfo(
        id='PUBLIC_NETWORK',
        name='PUBLIC_NETWORK',
        status='ACTIVE',
        subnets=[FAKE_SUBNETS['PUBLIC_SUBNET'].serialize()]
    ),

    'PRIVATE_NETWORK': base.NetworkInfo(
        id='PRIVATE_NETWORK',
        name='PRIVATE_NETWORK',
        status='ACTIVE',
        subnets=[FAKE_SUBNETS['PRIVATE_SUBNET'].serialize()]
    ),

    'SERVICE_NETWORK': base.NetworkInfo(
        id='SERVICE_NETWORK',
        name='SERVICE_NETWORK',
        status='ACTIVE',
        subnets=[FAKE_SUBNETS['SERVICE_SUBNET'].serialize()]
    )
}

FAKE_PORT = base.PortInfo(
    id="FAKE_PORT",
    name="FAKE_PORT",
    status="ACTIVE",
    mac_address="a:b:c:d",
    fixed_ips=[{"subnet_id": "PUBLIC_SUBNET", "ip_address": "10.0.0.2"}],
    network=FAKE_NETWORKS['PUBLIC_NETWORK'].serialize()
)

DEFAULT_NETWORKS = ["PUBLIC_NETWORK", "PRIVATE_NETWORK"]
SERVICE_NETWORK = "SERVICE_NETWORK"


class FakeNetworkProvider(base.BaseNetworkProvider):
    def __init__(self, config):
        super(FakeNetworkProvider, self).__init__(config)
        self.log = structlog.get_logger()

    def attach(self, mac_address, network_id):
        return FAKE_PORT

    def detach(self, mac_address, network_id=None):
        pass

    def list_ports(self, mac_address):
        return [FAKE_PORT]

    def get_network_info(self, network_id):
        try:
            return FAKE_NETWORKS[network_id]
        except KeyError:
            raise self.NetworkDoesNotExist()

    def list_networks(self):
        return FAKE_NETWORKS.values()

    def get_default_networks(self):
        return DEFAULT_NETWORKS

    def get_service_network(self):
        return SERVICE_NETWORK
