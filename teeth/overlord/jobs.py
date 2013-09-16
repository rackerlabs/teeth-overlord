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


class Job(object):
    def execute():
        raise NotImplementedError()


class CreateInstanceJob(Job):
    def __init__(self, instance):
        self.instance = instance

    def find_chassis(self):
        ready_query = models.Chassis.objects \
                                    .filter(state=models.ChassisState.READY)
        return threads.deferToThread(ready_query.first)

    def update_models(self, chassis):
        if not chassis:
            raise errors.InsufficientCapacityError()

        batch = BatchQuery()
        self.instance.chassis_id = chassis.id
        self.instance.state = models.InstanceState.ACTIVE
        self.instance.batch(batch).save()
        chassis.state = models.ChassisState.ACTIVE
        chassis.batch(batch).save()
        return threads.deferToThread(batch.execute)

    def done(self, _):
        return self.instance

    def execute(self):
        # TODO: return before the instance is done provisioning
        return self.find_chassis() \
                   .addCallbacks(self.update_models) \
                   .addCallback(self.done)
