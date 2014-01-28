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

import abc
import collections

from stevedore import driver


class NetworkInfo(object):

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.status = kwargs.get('status')
        self.subnets = kwargs.get('subnets')

    def serialize(self):
        """Turn a NetworkInfo into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('name', self.name),
            ('status', self.status),
            ('subnets', self.subnets)
        ])


class SubnetInfo(object):

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.ip_version = kwargs.get('ip_version')
        self.gateway_ip = kwargs.get('gateway_ip')
        self.cidr = kwargs.get('cidr')
        self.enable_dhcp = kwargs.get('enable_dhcp')

    def serialize(self):
        """Turn a SubnetInfo into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('name', self.name),
            ('ip_version', self.ip_version),
            ('gateway_ip', self.gateway_ip),
            ('cidr', self.cidr),
            ('enable_dhcp', self.enable_dhcp)
        ])


class PortInfo(object):

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.status = kwargs.get('status')
        self.fixed_ips = kwargs.get('fixed_ips')
        self.mac_address = kwargs.get('mac_address')
        self.network = kwargs.get('network')

    def serialize(self):
        """Turn a PortInfo into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('name', self.name),
            ('status', self.status),
            ('mac_address', self.mac_address),
            ('fixed_ips', self.fixed_ips),
            ('network', self.network)
        ])


class BaseNetworkProvider(object):
    """Provides support for network operations."""

    __metaclass__ = abc.ABCMeta

    class NetworkProviderException(Exception):
        pass

    class NetworkDoesNotExist(NetworkProviderException):
        pass

    class SubnetDoesNotExist(NetworkProviderException):
        pass

    def __init__(self, config):
        self.config = config

    @abc.abstractmethod
    def attach(self, chassis, network_id):
        """Attach to a given network."""
        pass

    @abc.abstractmethod
    def detach(self, chassis, network_id=None):
        """Detatch from a given network."""
        pass

    @abc.abstractmethod
    def list_networks(self):
        """List avaiable networks."""
        pass

    @abc.abstractmethod
    def get_network_info(self, network_id):
        """Get info about a network."""
        pass

    @abc.abstractmethod
    def list_ports(self, mac_address):
        """Get port information about a given mac address."""

    @abc.abstractmethod
    def get_default_networks(self):
        """Get list of default network_ids for new instances."""
        pass

    @abc.abstractmethod
    def get_service_network(self):
        """Get the service network id."""
        pass


def get_network_provider(config):
    mgr = driver.DriverManager(
        namespace='teeth_overlord.network.providers',
        name=config.NETWORK_PROVIDER,
        invoke_on_load=True,
        invoke_args=[config],
    )
    return mgr.driver
