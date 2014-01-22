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

import cqlengine

from teeth_overlord.jobs import base
from teeth_overlord import models
from teeth_overlord import stats


class CreateInstance(base.Job):

    """Job which creates an instance. In order to return a 201 response
    to the user, we actually create an Instance in the database in the
    `BUIlD` state prior to executing this job, but it is up to the job
    to select and provision an appropriate chassis based on the instance
    parameters.
    """
    max_retries = 10

    def attach_networks(self, instance, chassis):

        for network in instance.network_ids:
            self.executor.network_provider.attach(
                chassis.primary_mac_address,
                network)

    def prepare_and_run_image(self, instance, chassis, image_info):
        """Send the `prepare_image` and `run_image` commands to the agent."""
        client = self.executor.agent_client
        agent = client.get_agent(chassis)
        client.prepare_image(agent, image_info)
        client.run_image(agent, image_info)

    def mark_active(self, instance, chassis):
        """Mark the chassis and instance as active."""
        batch = cqlengine.BatchQuery()
        instance.chassis_id = chassis.id
        instance.state = models.InstanceState.ACTIVE
        instance.batch(batch).save()
        chassis.state = models.ChassisState.ACTIVE
        chassis.instance_id = instance.id
        chassis.batch(batch).save()
        batch.execute()

    @stats.incr_stat('instances.create')
    def _execute(self):
        params = self.request.params
        instance = models.Instance.objects.get(id=params['instance_id'])
        image_id = instance.image_id
        chassis = self.executor.scheduler.reserve_chassis(instance)
        image_info = self.executor.image_provider.get_image_info(image_id)

        self.attach_networks(instance, chassis)
        # TODO(morgabra): After booting into an image, we need to detach
        #                 from the service network.
        self.prepare_and_run_image(instance, chassis, image_info)
        self.mark_active(instance, chassis)


class DeleteInstance(base.Job):

    """Job which deletes an instance.

    Prior to the job being submitted, the Instance in the database will
    be put in the `DELETING` state.
    """
    max_retries = 10

    @stats.incr_stat('instances.delete')
    def _execute(self):
        params = self.request.params
        instance = models.Instance.objects.get(id=params['instance_id'])
        chassis = models.Chassis.objects.get(id=instance.chassis_id)

        batch = cqlengine.BatchQuery()
        instance.state = models.InstanceState.DELETED
        instance.batch(batch).save()
        chassis.state = models.ChassisState.CLEAN
        chassis.batch(batch).save()
        batch.execute()
        self.executor.oob_provider.power_chassis_off(chassis)
        self.executor.job_client.submit_job('chassis.decommission',
                                            chassis_id=chassis.id)
        return
