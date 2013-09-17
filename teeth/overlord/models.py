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

import uuid
from collections import OrderedDict

from cqlengine import columns
from cqlengine.models import Model

from teeth.overlord.encoding import Serializable

KEYSPACE_NAME = 'teeth'


class Base(Model, Serializable):
    __abstract__ = True
    __keyspace__ = KEYSPACE_NAME


class ChassisState(object):
    CLEAN = 'CLEAN'
    READY = 'READY'
    BUILD = 'BUILD'
    ACTIVE = 'ACTIVE'


class Chassis(Base):
    id = columns.UUID(primary_key=True, default=uuid.uuid4)
    state = columns.Ascii(index=True, default=ChassisState.READY)
    primary_mac_address = columns.Ascii(index=True, required=True)

    def serialize(self, view):
        return OrderedDict([
            ('id', str(self.id)),
            ('state', self.state),
        ])


class InstanceState(object):
    BUILD = 'BUILD'
    ACTIVE = 'ACTIVE'


class Instance(Base):
    id = columns.UUID(primary_key=True, default=uuid.uuid4)
    chassis_id = columns.UUID()
    state = columns.Ascii(default=InstanceState.BUILD)

    def serialize(self, view):
        return OrderedDict([
            ('id', str(self.id)),
            ('chassis_id', str(self.chassis_id)),
            ('state', self.state),
        ])


class AgentConnection(Base):
    # This is funky, the ID isn't the primary key. We want to be able to
    # overwrite these using nothing but the MAC address, so we use that as the
    # primary key, but set an indexed 'id' field for consistency.
    id = columns.UUID(index=True, default=uuid.uuid4)
    primary_mac_address = columns.Ascii(primary_key=True)
    agent_version = columns.Ascii(required=True)
    endpoint_rpc_host = columns.Ascii(required=True)
    endpoint_rpc_port = columns.Integer(required=True)

    def serialize(self, view):
        return OrderedDict([
            ('id', str(self.id)),
            ('primary_mac_address', self.primary_mac_address),
            ('endpoint_rcp_host', self.endpoint_rpc_host),
            ('endpoint_rpc_port', self.endpoint_rpc_port),
        ])


all_models = [Chassis, Instance, AgentConnection]
