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

from structlog import get_logger

from teeth_overlord.oob.base import BaseOutOfBandProvider


class FakeOutOfBandProvider(BaseOutOfBandProvider):
    """
    Provides support for out-of-band operations.
    """
    def __init__(self, config):
        super(FakeOutOfBandProvider, self).__init__(config)
        self.log = get_logger()

    def is_chassis_on(self, chassis):
        """
        Returns a boolean indicating whether a chassis is on.
        """
        return True

    def power_chassis_off(self, chassis):
        """
        Power a chassis off.
        """
        self.log.info('faking chassis power-off command', chassis_id=chassis.id)
        return True

    def power_chassis_on(self, chassis):
        """
        Power a chassis on.
        """
        self.log.info('faking chassis power-on command', chassis_id=chassis.id)
        return True
