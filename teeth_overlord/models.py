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
import datetime
import struct
import uuid

import cqlengine
from cqlengine import columns
from cqlengine import models

from teeth_rest import encoding

KEYSPACE_NAME = 'teeth'

MAX_ID_LENGTH = 64

MAX_METADATA_KEY_COUNT = 8

MAX_METADATA_KEY_LENGTH = 512

MAX_METADATA_VALUE_LENGTH = 2048


def uuid_str():
    """Generate a string containing a serialized v4 UUID."""
    return str(uuid.uuid4())


class C2DateTime(columns.DateTime):
    """Hack until cqlengine supports Cassandra 2.0. See:
    http://stackoverflow.com/a/18992934
    """

    def to_python(self, val):
        """Turn the raw database value into a Python DateTime."""
        if isinstance(val, basestring):
            val = struct.unpack('!Q', val)[0] / 1000.0
        return super(C2DateTime, self).to_python(val)


class Base(models.Model, encoding.Serializable):
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
            raise cqlengine.ValidationError(
                "Exceeded limit of {} 'metadata' keys.".format(
                    MAX_METADATA_KEY_COUNT))


class ChassisState(object):
    """Possible states that a Chassis may be in."""
    BOOTSTRAP = 'BOOTSTRAP'
    CLEAN = 'CLEAN'
    READY = 'READY'
    BUILD = 'BUILD'
    ACTIVE = 'ACTIVE'
    DELETED = 'DELETED'


class Flavor(Base):
    """Model for flavors. Users choose a Flavor when they create an
    instance.
    """
    id = columns.Text(primary_key=True,
                      default=uuid_str,
                      max_length=MAX_ID_LENGTH)
    name = columns.Text(required=True)
    deleted = columns.Boolean(index=True, required=True, default=False)

    def serialize(self, view):
        """Turn a Flavor into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('name', self.name),
            ('deleted', self.deleted)
        ])

    @classmethod
    def deserialize(cls, params):
        """Turn a dict into a Flavor."""
        flavor = cls(
            id=params.get('id'),
            name=params.get('name')
        )
        flavor.validate()
        return flavor


class FlavorProvider(Base):
    """Model which joins Flavors to ChassisModels.

    When an instance is created, a list of FlavorProviders will be
    looked up based on the specified flavor. The included
    `schedule_priority` can be used to select the highest priority
    ChassisModel capable of providing the specified flavor.
    Theoretically, this could allow a certain chassis model to
    provide multiple flavors, or a flavor to be provided by multiple
    chassis models.
    """
    id = columns.Text(primary_key=True,
                      default=uuid_str,
                      max_length=MAX_ID_LENGTH)
    flavor_id = columns.Text(index=True,
                             required=True,
                             max_length=MAX_ID_LENGTH)
    chassis_model_id = columns.Text(index=True,
                                    required=True,
                                    max_length=MAX_ID_LENGTH)
    schedule_priority = columns.Integer(required=True)
    deleted = columns.Boolean(index=True, required=True, default=False)

    def serialize(self, view):
        """Turn a FlavorProvider into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('flavor_id', self.flavor_id),
            ('chassis_model_id', self.chassis_model_id),
            ('schedule_priority', self.schedule_priority),
            ('deleted', self.deleted)
        ])

    @classmethod
    def deserialize(cls, params):
        """Turn a dict into a FlavorProvider."""
        flavor_provider = cls(
            flavor_id=params.get('flavor_id'),
            chassis_model_id=params.get('chassis_model_id'),
            schedule_priority=params.get('schedule_priority')
        )
        flavor_provider.validate()
        return flavor_provider


class ChassisModel(Base):
    """Model which represents a Chassis Model. For example, a Dell R720.

    ChassisModels include default IPMI credentials, which will be used
    when initializing new hardware.
    """
    id = columns.Text(primary_key=True,
                      default=uuid_str,
                      max_length=MAX_ID_LENGTH)
    name = columns.Text(required=True)
    ipmi_default_password = columns.Text()
    ipmi_default_username = columns.Text()
    deleted = columns.Boolean(index=True, required=True, default=False)

    def serialize(self, view):
        """Turn a ChassisModel into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('name', self.name),
            ('deleted', self.deleted)
        ])

    @classmethod
    def deserialize(cls, params):
        """Turn a dict into a ChassisModel."""
        chassis_model = cls(
            id=params.get('id'),
            name=params.get('name'),
            ipmi_default_password=params.get('ipmi_default_password'),
            ipmi_default_username=params.get('ipmi_default_username')
        )
        chassis_model.validate()
        return chassis_model


class Switch(MetadataBase):
    """Model for a switch."""
    id = columns.Text(primary_key=True,
                      default=uuid_str,
                      max_length=MAX_ID_LENGTH)
    name = columns.Text(required=True)


class SwitchPort(MetadataBase):
    """Model for switch port.

    TODO(russellhaering): How should we represent MLAG pairs?
    """
    id = columns.Text(primary_key=True,
                      default=uuid_str,
                      max_length=MAX_ID_LENGTH)
    name = columns.Text(required=True)
    switch_id = columns.Text(required=True, max_length=MAX_ID_LENGTH)


class Chassis(MetadataBase):
    """Model for an individual Chassis."""
    id = columns.Text(primary_key=True,
                      default=uuid_str,
                      max_length=MAX_ID_LENGTH)
    state = columns.Ascii(index=True,
                          default=ChassisState.READY)
    chassis_model_id = columns.Text(index=True,
                                    required=True,
                                    max_length=MAX_ID_LENGTH)
    instance_id = columns.Text(max_length=MAX_ID_LENGTH)
    ipmi_host = columns.Text()
    ipmi_port = columns.Integer(default=623)
    ipmi_username = columns.Text()
    ipmi_password = columns.Text()

    def serialize(self, view):
        """Turn a Chassis into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('state', self.state),
            ('chassis_model_id', self.chassis_model_id),
            ('instance_id', self.instance_id),
            ('metadata', self.metadata),
        ])

    @classmethod
    def deserialize(cls, params):
        """Turn a dict into a Chassis."""
        chassis = cls(
            id=params.get('id'),
            chassis_model_id=params.get('chassis_model_id'),
            metadata=params.get('metadata')
        )
        chassis.validate()
        return chassis

    @classmethod
    def find_by_hardware(cls, hardware):
        """Finds a chassis uniquely matching every key in `hardware`.

        If a chassis is not found, a new one is created in
        a BOOTSTRAP state.
        """
        groups = []
        for k, v in hardware.items():
            found = HardwareToChassis.objects.filter(hardware_type=k,
                                                     hardware_id=v)
            found = set(h2c.chassis_id for h2c in found)
            groups.append(found)

        matches = found[0].union(*found[1:])

        if len(matches) > 1:
            raise errors.SomeHorribleException
        if len(matches) == 1:
            return cls.objects.get(id=matches.pop())

        # TODO(jimrollenhagen) if no matches, create a chassis


class HardwareToChassis(Base):
    """Map of hardware (key/value) to Chassis."""
    hardware_type = columns.Text(partition_key=True, required=True)
    hardware_id = columns.Text(partition_key=True, required=True)
    chassis_id = columns.Text(primary_key=True,
                              required=True,
                              max_length=MAX_ID_LENGTH)

    def serialize(self, view):
        """Turn a Chassis into a dict."""
        return collections.OrderedDict([
            ('hardware_type', self.hardware_type),
            ('hardware_id', self.hardware_id),
            ('chassis_id', self.chassis_id)
        ])

    @classmethod
    def deserialize(cls, params):
        """Turn a dict into a Chassis."""
        m = cls(
            hardware_type=params.get('hardware_type'),
            hardware_id=params.get('hardware_id'),
            chassis_id=params.get('chassis_id')
        )
        m.validate()
        return m


class InstanceState(object):
    """Possible states than an Instance can be in."""
    BUILD = 'BUILD'
    ACTIVE = 'ACTIVE'
    DELETING = 'DELETING'
    DELETED = 'DELETED'


class Instance(MetadataBase):
    """Model for an Instance."""
    id = columns.Text(primary_key=True,
                      default=uuid_str,
                      max_length=MAX_ID_LENGTH)
    name = columns.Text(required=True)
    flavor_id = columns.Text(required=True, max_length=MAX_ID_LENGTH)
    image_id = columns.Text(required=True, max_length=MAX_ID_LENGTH)
    chassis_id = columns.Text(max_length=MAX_ID_LENGTH)
    network_ids = columns.Set(columns.Text, required=True, strict=False)
    state = columns.Ascii(index=True, default=InstanceState.BUILD)

    def serialize(self, view):
        """Turn an Instance into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('name', self.name),
            ('flavor_id', self.flavor_id),
            ('image_id', self.image_id),
            ('chassis_id', self.chassis_id),
            ('network_ids', list(self.network_ids)),
            ('state', self.state),
            ('metadata', self.metadata),
        ])

    @classmethod
    def deserialize(cls, params):
        """Turn a dict into an Instance."""
        instance = cls(
            id=params.get('id'),
            name=params.get('name'),
            flavor_id=params.get('flavor_id'),
            image_id=params.get('image_id'),
            network_ids=params.get('network_ids'),
            metadata=params.get('metadata'),
        )

        instance.validate()
        return instance


class AgentState(object):
    """Possible states that an Agent can be in."""
    STANDBY = 'STANDBY'
    DECOM = 'DECOM'


class Agent(Base):
    """Model for an Agent."""
    TTL = 180
    id = columns.Text(primary_key=True,
                      default=uuid_str,
                      max_length=MAX_ID_LENGTH)
    version = columns.Ascii(required=True)
    url = columns.Ascii(required=True)
    mode = columns.Ascii(required=True, index=True)
    chassis_id = columns.Text(max_length=MAX_ID_LENGTH)

    def serialize(self, view):
        """Turn an Agent into a dict."""
        return collections.OrderedDict([
            ('version', self.version),
            ('url', self.url),
            ('mode', self.mode),
            ('chassis_id', self.chassis_id),
        ])


class JobRequestState(object):
    """Possible states that JobRequest can be in."""
    READY = 'READY'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class JobRequest(Base):
    """Model for a Job Request."""
    id = columns.Text(primary_key=True,
                      default=uuid_str,
                      max_length=MAX_ID_LENGTH)
    job_type = columns.Ascii(required=True)
    params = columns.Map(columns.Ascii, columns.Ascii)
    state = columns.Ascii(index=True, default=JobRequestState.READY)
    failed_attempts = columns.Integer(default=0)
    submitted_at = C2DateTime(default=datetime.datetime.now)
    updated_at = C2DateTime(default=datetime.datetime.now)

    def serialize(self, view):
        """Turn a JobRequest into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('job_type', self.job_type),
            ('params', self.params.to_python),
        ])

    def touch(self):
        """Update the `udpated_at` field.

        Note: this does not save the JobRequest.
        """
        self.updated_at = datetime.datetime.now()

    def start(self):
        """Mark the job as `RUNNING` and update the `udpated_at` field.

        Note: this does not save the JobRequest.
        """
        self.state = JobRequestState.RUNNING
        self.touch()

    def reset(self):
        """Mark mark the job as `READY` and update the `updated_at` field.

        Note: this does not save the JobRequest.
        """
        if self.state != JobRequestState.READY:
            self.failed_attempts += 1
        self.state = JobRequestState.READY
        self.touch()

    def fail(self):
        """Mark the job as `FAILED` and update the `udpated_at` field.

        Note: this does not save the JobRequest.
        """
        self.state = JobRequestState.FAILED
        self.touch()

    def complete(self):
        """Mark the job as `COMPLETED` and update the `udpated_at` field.

        Note: this does not save the JobRequest.
        """
        self.state = JobRequestState.COMPLETED
        self.touch()

all_models = [
    Chassis,
    HardwareToChassis,
    Instance,
    Agent,
    JobRequest,
    Flavor,
    FlavorProvider,
    ChassisModel
]
