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

import random

import cqlengine
import structlog

from teeth_overlord import errors
from teeth_overlord import models


class TeethInstanceScheduler(object):
    """Schedule instances onto chassis."""
    def __init__(self):
        self.log = structlog.get_logger()

    def reserve_chassis(self, instance, retry=True):
        """Locate and reserve a chassis for the specified instance."""

        attempts = 0

        while True:
            chassis = self._retrieve_eligible_chassis(instance)
            try:
                attempts = attempts + 1
                return self._mark_chassis_reserved(chassis, instance)
            except errors.ChassisAlreadyReservedError as e:
                if not retry:
                    raise e
                continue

    def _get_flavor_provider_priority(self, flavor_provider):
        return flavor_provider.schedule_priority

    def _retrieve_eligible_chassis(self, instance):
        """Retrieve an available Chassis suitable for the instance."""

        # Sort flavor providers by priority
        flavor_provider_query = models.FlavorProvider.objects.allow_filtering()
        flavor_provider_query = flavor_provider_query.filter(
            flavor_id=instance.flavor_id, deleted=False)

        flavor_providers = sorted(flavor_provider_query,
                                  key=self._get_flavor_provider_priority,
                                  reverse=True)

        for flavor_provider in flavor_providers:
            chassis_list = models.Chassis.objects
            chassis_list = chassis_list.filter(state=models.ChassisState.READY)
            chassis_list = chassis_list.filter(
                chassis_model_id=flavor_provider.chassis_model_id)
            chassis_list = chassis_list.allow_filtering()

            if len(chassis_list) > 0:
                # Choose a random chassis from among those most suitable.
                return random.choice(chassis_list)

        raise errors.InsufficientCapacityError()

    def _mark_chassis_reserved(self, chassis, instance):
        """Mark the selected chassis as belonging to this instance, and
        put it into a `BUILD` state.
        """
        # TODO(russellhaering): Lock around instance reservation
        # self.lock_manager.lock('/chassis/{chassis_id}'.format(
        #     chassis_id=str(chassis.id)
        # ))

        # Re-fetch the chassis while we hold the lock
        chassis = models.Chassis.objects.filter(id=chassis.id).get()

        if chassis.state != models.ChassisState.READY:
            raise errors.ChassisAlreadyReservedError(chassis)

        batch = cqlengine.BatchQuery()
        instance.chassis_id = chassis.id
        instance.state = models.InstanceState.INACTIVE
        instance.batch(batch).save()
        chassis.state = models.ChassisState.BUILD
        chassis.batch(batch).save()
        batch.execute()

        # TODO(russellhaering): unlock
        return chassis
