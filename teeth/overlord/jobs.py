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

from twisted.internet import threads
from cqlengine import BatchQuery

from teeth.overlord import models
from teeth.overlord import errors
from teeth.overlord.agent.rpc import EndpointRPCClient


class Job(object):
    """
    TODO: implement reliable job execution, either by persisting these or by
    using something like Celery.
    """
    def execute():
        raise NotImplementedError()


class CreateInstanceJob(Job):
    def __init__(self, instance, config):
        self.instance = instance
        self.endpoint_rpc = EndpointRPCClient(config)

    def find_chassis(self):
        ready_query = models.Chassis.objects.filter(state=models.ChassisState.READY)
        return threads.deferToThread(ready_query.first)

    def reserve_chassis(self, chassis):
        if not chassis:
            raise errors.InsufficientCapacityError()

        batch = BatchQuery()
        self.instance.chassis_id = chassis.id
        self.instance.state = models.InstanceState.BUILD
        self.instance.batch(batch).save()
        chassis.state = models.ChassisState.BUILD
        chassis.batch(batch).save()
        return threads.deferToThread(batch.execute).addCallback(lambda result: chassis)

    def prepare_image(self, chassis):
        connection_query = models.AgentConnection.objects.filter(primary_mac_address=chassis.primary_mac_address)

        def _with_connection(connection):
            return self.endpoint_rpc.prepare_image(connection, 'image-123').addCallback(lambda result: chassis)

        return threads.deferToThread(connection_query.first).addCallback(_with_connection)

    def mark_active(self, chassis):
        if not chassis:
            raise errors.InsufficientCapacityError()

        batch = BatchQuery()
        self.instance.chassis_id = chassis.id
        self.instance.state = models.InstanceState.ACTIVE
        self.instance.batch(batch).save()
        chassis.state = models.ChassisState.ACTIVE
        chassis.batch(batch).save()
        return threads.deferToThread(batch.execute).addCallback(lambda result: chassis)

    def done(self, _):
        return self.instance

    def execute(self):
        # TODO: return before the instance is done provisioning
        return self.find_chassis() \
                   .addCallback(self.reserve_chassis) \
                   .addCallback(self.prepare_image) \
                   .addCallback(self.mark_active) \
                   .addCallback(self.done)
