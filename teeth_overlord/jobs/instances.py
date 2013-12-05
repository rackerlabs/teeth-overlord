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

from cqlengine import BatchQuery

from teeth_overlord.models import (
    ChassisState,
    Instance,
    InstanceState
)
from teeth_overlord.jobs.base import Job


class CreateInstance(Job):
    """
    Job which creates an instance. In order to return a 201 response to
    the user, we actually create an Instance in the database in the
    `BUIlD` state prior to executing this job, but it is up to the job
    to select and provision an appropriate chassis based on the instance
    parameters.
    """
    max_retries = 10

    def prepare_and_run_image(self, instance, chassis, image_info):
        """
        Send the `prepare_image` and `run_image` commands to the agent.
        """
        client = self.executor.agent_client
        connection = client.get_agent_connection(chassis)
        client.prepare_image(connection, image_info)
        client.run_image(connection, image_info)
        return

    def mark_active(self, instance, chassis):
        """
        Mark the chassis and instance as active.
        """
        batch = BatchQuery()
        instance.chassis_id = chassis.id
        instance.state = InstanceState.ACTIVE
        instance.batch(batch).save()
        chassis.state = ChassisState.ACTIVE
        chassis.batch(batch).save()
        batch.execute()
        return

    def _execute(self):
        params = self.request.params
        instance = Instance.objects.get(id=params['instance_id'])
        chassis = self.executor.scheduler.reserve_chassis(instance)
        image_info = self.executor.image_provider.get_image_info(instance.image_id)

        self.prepare_and_run_image(instance, chassis, image_info)
        self.mark_active(instance, chassis)
        return
