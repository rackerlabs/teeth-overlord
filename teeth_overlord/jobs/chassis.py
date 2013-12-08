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

from teeth_overlord.models import (
    Chassis,
    ChassisState,
)
from teeth_overlord.jobs.base import Job


class DecommissionChassis(Job):
    """
    Job which processes a Chassis from the `CLEAN` state to the `READY` state.
    """
    max_retries = 10

    def _execute(self):
        params = self.request.params
        chassis = Chassis.objects.get(id=params['chassis_id'])

        if chassis.state != ChassisState.CLEAN:
            self.log.info('chassis not in CLEAN state, skipping', current_state=chassis.state)

        # TODO: perform on-server decommissioning
        # TODO: rotate IPMI password?

        chassis.state = ChassisState.READY
        chassis.save()
        return
