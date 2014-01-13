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

from carbide_overlord.jobs import base
from carbide_overlord import models
from carbide_overlord import stats


class DecommissionChassis(base.Job):

    """Job which processes a Chassis from the `CLEAN` state to the
    `READY` state.
    """
    max_retries = 10

    @stats.incr_stat('chassis.decommission')
    def _execute(self):
        params = self.request.params
        chassis = models.Chassis.objects.get(id=params['chassis_id'])

        if chassis.state != models.ChassisState.CLEAN:
            self.log.info('chassis not in CLEAN state, skipping',
                          current_state=chassis.state)
            return

        if self.executor.oob_provider.is_chassis_on(chassis):
            self.executor.oob_provider.power_chassis_off(chassis)

        # TODO(russellhaering): Move Chassis to the decom network

        self.executor.oob_provider.power_chassis_on(chassis)

        # TODO(russellhaering): perform on-server decommissioning
        # TODO(russellhaering): rotate IPMI password?

        self.log.info('chassis cleaned, moving to standby network',
                      chassis_id=chassis.id)
        self.executor.oob_provider.power_chassis_off(chassis)
        # TODO(russellhaering): move chassis to standby network
        self.executor.oob_provider.power_chassis_on(chassis)

        chassis.state = models.ChassisState.READY
        # Dissassociate any instances after clean completes.
        chassis.instance_id = None
        chassis.save()
        return
