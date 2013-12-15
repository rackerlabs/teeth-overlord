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

from collections import OrderedDict
from datetime import datetime
from uuid import uuid4
import struct

from cqlengine import ValidationError, columns
from cqlengine.models import Model

from teeth_rest.encoding import Serializable

KEYSPACE_NAME = 'teeth'

MAX_ID_LENGTH = 64

MAX_METADATA_KEY_COUNT = 8

MAX_METADATA_KEY_LENGTH = 512

MAX_METADATA_VALUE_LENGTH = 2048


def uuid_str():
    """
    Generate a string containing a serialized v4 UUID.
    """
    return str(uuid4())


class C2DateTime(columns.DateTime):
    """
    Hack until cqlengine supports Cassandra 2.0. See:
    http://stackoverflow.com/a/18992934
    """

    def to_python(self, val):
        """Turn the raw database value into a Python DateTime."""
        if isinstance(val, basestring):
            val = struct.unpack('!Q', val)[0] / 1000.0
        return super(C2DateTime, self).to_python(val)


class Base(Model, Serializable):
    """Base class for all Teeth models."""
    __abstract__ = True
    __keyspace__ = KEYSPACE_NAME


class MetadataBase(Base):
    __abstract__ = True

    metadata = columns.Map(
        columns.Text(max_length=MAX_METADATA_KEY_LENGTH),
        columns.Text(max_length=MAX_METADATA_VALUE_LENGTH))

    def validate(self):
        super(MetadataBase, self).validate()

        if len(self.metadata) > MAX_METADATA_KEY_COUNT:
            raise ValidationError("Exceeded limit of {} 'metadata' keys.".format(MAX_METADATA_KEY_COUNT))


class ChassisState(object):
    """Possible states that a Chassis may be in."""
    CLEAN = 'CLEAN'
    READY = 'READY'
    BUILD = 'BUILD'
    ACTIVE = 'ACTIVE'


class Flavor(Base):
    """
    Model for flavors. Users choose a Flavor when they create an instance.
    """
    id = columns.Text(primary_key=True, default=uuid_str, max_length=MAX_ID_LENGTH)
    name = columns.Text(required=True)

    def serialize(self, view):
        """
        Turn a Flavor into a dict.
        """
        return OrderedDict([
            ('id', self.id),
            ('name', self.name),
        ])

    @classmethod
    def deserialize(cls, params):
        """
        Turn a dict into a Flavor.
        """
        flavor = cls(
            name=params.get('name')
        )
        flavor.validate()
        return flavor


class FlavorProvider(Base):
    """
    Model which joins Flavors to ChassisModels.

    When an instance is created, a list of FlavorProviders will be
    looked up based on the specified flavor. The included
    `schedule_priority` can be used to select the highest priority
    ChassisModel capable of providing the specified flavor.
    Theoretically, this could allow a certain chassis model to
    provide multiple flavors, or a flavor to be provided by multiple
    chassis models.
    """
    id = columns.Text(primary_key=True, default=uuid_str, max_length=MAX_ID_LENGTH)
    flavor_id = columns.Text(index=True, required=True, max_length=MAX_ID_LENGTH)
    chassis_model_id = columns.Text(index=True, required=True, max_length=MAX_ID_LENGTH)
    schedule_priority = columns.Integer(required=True)

    def serialize(self, view):
        """
        Turn a FlavorProvider into a dict.
        """
        return OrderedDict([
            ('id', self.id),
            ('flavor_id', self.flavor_id),
            ('chassis_model_id', self.chassis_model_id),
            ('schedule_priority', self.schedule_priority),
        ])

    @classmethod
    def deserialize(cls, params):
        """
        Turn a dict into a FlavorProvider.
        """
        flavor_provider = cls(
            flavor_id=params.get('flavor_id'),
            chassis_model_id=params.get('chassis_model_id'),
            schedule_priority=params.get('schedule_priority')
        )
        flavor_provider.validate()
        return flavor_provider


class ChassisModel(Base):
    """
    Model which represents a Chassis Model. For example, a Dell R720.

    ChassisModels include default IPMI credentials, which will be used
    when initializing new hardware.
    """
    id = columns.Text(primary_key=True, default=uuid_str, max_length=MAX_ID_LENGTH)
    name = columns.Text(required=True)
    ipmi_default_password = columns.Text()
    ipmi_default_username = columns.Text()

    def serialize(self, view):
        """
        Turn a ChassisModel into a dict.
        """
        return OrderedDict([
            ('id', self.id),
            ('name', self.name),
        ])

    @classmethod
    def deserialize(cls, params):
        """
        Turn a dict into a ChassisModel.
        """
        chassis_model = cls(
            name=params.get('name'),
            ipmi_default_password=params.get('ipmi_default_password'),
            ipmi_default_username=params.get('ipmi_default_username')
        )
        chassis_model.validate()
        return chassis_model


class Chassis(MetadataBase):
    """
    Model for an individual Chassis.
    """
    id = columns.Text(primary_key=True, default=uuid_str, max_length=MAX_ID_LENGTH)
    state = columns.Ascii(index=True, default=ChassisState.READY)
    chassis_model_id = columns.Text(index=True, required=True, max_length=MAX_ID_LENGTH)
    ipmi_username = columns.Text()
    ipmi_password = columns.Text()
    primary_mac_address = columns.Ascii(index=True, required=True)

    def serialize(self, view):
        """
        Turn a Chassis into a dict.
        """
        return OrderedDict([
            ('id', self.id),
            ('state', self.state),
            ('chassis_model_id', self.chassis_model_id),
            ('primary_mac_address', self.primary_mac_address),
            ('metadata', self.metadata),
        ])

    @classmethod
    def deserialize(cls, params):
        """
        Turn a dict into a Chassis.
        """
        chassis = cls(
            chassis_model_id=params.get('chassis_model_id'),
            primary_mac_address=params.get('primary_mac_address'),
            metadata=params.get('metadata')
        )
        chassis.validate()
        return chassis


class InstanceState(object):
    """
    Possible states than an Instance can be in.
    """
    BUILD = 'BUILD'
    ACTIVE = 'ACTIVE'
    DELETING = 'DELETING'
    DELETED = 'DELETED'


class Instance(MetadataBase):
    """
    Model for an Instance.
    """
    id = columns.Text(primary_key=True, default=uuid_str, max_length=MAX_ID_LENGTH)
    name = columns.Text(required=True)
    flavor_id = columns.Text(required=True, max_length=MAX_ID_LENGTH)
    image_id = columns.Text(required=True, max_length=MAX_ID_LENGTH)
    chassis_id = columns.Text(max_length=MAX_ID_LENGTH)
    state = columns.Ascii(index=True, default=InstanceState.BUILD)

    def serialize(self, view):
        """
        Turn an Instance into a dict.
        """
        return OrderedDict([
            ('id', self.id),
            ('name', self.name),
            ('flavor_id', self.flavor_id),
            ('image_id', self.image_id),
            ('chassis_id', self.chassis_id),
            ('state', self.state),
            ('metadata', self.metadata),
        ])

    @classmethod
    def deserialize(cls, params):
        """
        Turn a dict into an Instance.
        """
        instance = cls(
            name=params.get('name'),
            flavor_id=params.get('flavor_id'),
            image_id=params.get('image_id'),
            metadata=params.get('metadata'),
        )

        instance.validate()
        return instance


class AgentConnection(Base):
    """
    Model for an AgentConnection.

    Notably, the `id` field isn't the primary key. We want to be able to
    overwrite these using nothing but the MAC address, so we use that as
    the primary key, but set an indexed `id` field for consistency.
    """
    id = columns.Text(index=True, default=uuid_str, max_length=MAX_ID_LENGTH)
    primary_mac_address = columns.Ascii(primary_key=True)
    agent_version = columns.Ascii(required=True)
    endpoint_rpc_host = columns.Ascii(required=True)
    endpoint_rpc_port = columns.Integer(required=True)

    def serialize(self, view):
        """
        Turn an AgentConnection into a dict.
        """
        return OrderedDict([
            ('id', self.id),
            ('primary_mac_address', self.primary_mac_address),
            ('endpoint_rpc_host', self.endpoint_rpc_host),
            ('endpoint_rpc_port', self.endpoint_rpc_port),
        ])


class JobRequestState(object):
    """
    Possible states that JobRequest can be in.
    """
    READY = 'READY'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class JobRequest(Base):
    """
    Model for a Job Request.
    """
    id = columns.Text(primary_key=True, default=uuid_str, max_length=MAX_ID_LENGTH)
    job_type = columns.Ascii(required=True)
    params = columns.Map(columns.Ascii, columns.Ascii)
    state = columns.Ascii(index=True, default=JobRequestState.READY)
    failed_attempts = columns.Integer(default=0)
    submitted_at = C2DateTime(default=datetime.now)
    updated_at = C2DateTime(default=datetime.now)

    def serialize(self, view):
        """
        Turn a JobRequest into a dict.
        """
        return OrderedDict([
            ('id', self.id),
            ('job_type', self.job_type),
            ('params', self.params.to_python),
        ])

    def touch(self):
        """
        Update the `udpated_at` field.

        Note: this does not save the JobRequest.
        """
        self.updated_at = datetime.now()

    def start(self):
        """
        Mark the job as `RUNNING` and update the `udpated_at` field.

        Note: this does not save the JobRequest.
        """
        self.state = JobRequestState.RUNNING
        self.touch()

    def reset(self):
        """
        Mark mark the job as `READY` and update the `updated_at` field.

        Note: this does not save the JobRequest.
        """
        if self.state != JobRequestState.READY:
            self.failed_attempts += 1
        self.state = JobRequestState.READY
        self.touch()

    def fail(self):
        """
        Mark the job as `FAILED` and update the `udpated_at` field.

        Note: this does not save the JobRequest.
        """
        self.state = JobRequestState.FAILED
        self.touch()

    def complete(self):
        """
        Mark the job as `COMPLETED` and update the `udpated_at` field.

        Note: this does not save the JobRequest.
        """
        self.state = JobRequestState.COMPLETED
        self.touch()

all_models = [Chassis, Instance, AgentConnection, JobRequest, Flavor, FlavorProvider, ChassisModel]
