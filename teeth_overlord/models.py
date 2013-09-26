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

from teeth_overlord.encoding import Serializable

KEYSPACE_NAME = 'teeth'


class Base(Model, Serializable):
    __abstract__ = True
    __keyspace__ = KEYSPACE_NAME


class ChassisState(object):
    CLEAN = 'CLEAN'
    READY = 'READY'
    BUILD = 'BUILD'
    ACTIVE = 'ACTIVE'


class Flavor(Base):
    id = columns.UUID(primary_key=True, default=uuid.uuid4)
    name = columns.Text(required=True)

    def serialize(self, view):
        return OrderedDict([
            ('id', str(self.id)),
            ('name', self.name),
        ])

    @classmethod
    def deserialize(cls, params):
        flavor = cls(
            name=params.get('name')
        )
        flavor.validate()
        return flavor


class FlavorProvider(Base):
    id = columns.UUID(primary_key=True, default=uuid.uuid4)
    flavor_id = columns.UUID(index=True, required=True)
    chassis_model_id = columns.UUID(index=True, required=True)
    schedule_priority = columns.Integer(required=True)

    def serialize(self, view):
        return OrderedDict([
            ('id', str(self.id)),
            ('flavor_id', str(self.flavor_id)),
            ('chassis_model_id', str(self.chassis_model_id)),
            ('schedule_priority', self.schedule_priority),
        ])

    @classmethod
    def deserialize(cls, params):
        flavor_provider = cls(
            flavor_id=params.get('flavor_id'),
            chassis_model_id=params.get('chassis_model_id'),
            schedule_priority=params.get('schedule_priority')
        )
        flavor_provider.validate()
        return flavor_provider


class ChassisModel(Base):
    id = columns.UUID(primary_key=True, default=uuid.uuid4)
    name = columns.Text(required=True)
    ipmi_default_password = columns.Text()
    ipmi_default_username = columns.Text()

    def serialize(self, view):
        return OrderedDict([
            ('id', str(self.id)),
            ('name', self.name),
        ])

    @classmethod
    def deserialize(cls, params):
        chassis_model = cls(
            name=params.get('name'),
            ipmi_default_password=params.get('ipmi_default_password'),
            ipmi_default_username=params.get('ipmi_default_username')
        )
        chassis_model.validate()
        return chassis_model


class Chassis(Base):
    id = columns.UUID(primary_key=True, default=uuid.uuid4)
    state = columns.Ascii(index=True, default=ChassisState.READY)
    chassis_model_id = columns.UUID(index=True, required=True)
    ipmi_username = columns.Text()
    ipmi_password = columns.Text()
    primary_mac_address = columns.Ascii(index=True, required=True)

    def serialize(self, view):
        return OrderedDict([
            ('id', str(self.id)),
            ('state', self.state),
            ('chassis_model_id', str(self.chassis_model_id)),
            ('primary_mac_address', self.primary_mac_address),
        ])

    @classmethod
    def deserialize(cls, params):
        chassis = cls(
            chassis_model_id=params.get('chassis_model_id'),
            primary_mac_address=params.get('primary_mac_address')
        )
        chassis.validate()
        return chassis


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

    @classmethod
    def deserialize(cls, params):
        instance = cls()
        instance.validate()
        return instance


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
            ('endpoint_rpc_host', self.endpoint_rpc_host),
            ('endpoint_rpc_port', self.endpoint_rpc_port),
        ])


class JobRequest(Base):
    id = columns.UUID(primary_key=True, default=uuid.uuid4)
    job_type = columns.Ascii(required=True)
    params = columns.Map(columns.Ascii, columns.Ascii)

    def serialize(self, view):
        return OrderedDict([
            ('id', str(self.id)),
            ('job_type', self.job_type),
            ('params', self.params.to_python),
        ])

all_models = [Chassis, Instance, AgentConnection, JobRequest, Flavor, FlavorProvider, ChassisModel]
