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

import simplejson as json
from cqlengine import columns
from cqlengine.models import Model

KEYSPACE_NAME = 'teeth'


class Serializable(object):
    def serialize(self, view):
        raise NotImplementedError()


class SerializationViews(object):
    PUBLIC = 'PUBLIC'


class ModelEncoder(json.JSONEncoder):
    def __init__(self, view):
        json.JSONEncoder.__init__(self, indent=4)
        self.view = view

    def default(self, o):
        if isinstance(o, Serializable):
            return o.serialize(self.view)
        else:
            return json.JSONEncoder.default(self, o)


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


all_models = [Chassis, Instance]
