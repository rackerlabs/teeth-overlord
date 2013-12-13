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

import abc

from stevedore import driver


class BaseOutOfBandProvider(object):
    """
    Provides support for out-of-band operations.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        self.config = config

    @abc.abstractmethod
    def is_chassis_on(self, chassis):
        """
        Returns a boolean indicating whether the chassis is on.
        """
        pass

    @abc.abstractmethod
    def power_chassis_off(self, chassis):
        """
        Power a chassis off.
        """
        pass

    @abc.abstractmethod
    def power_chassis_on(self, chassis):
        """
        Power a chassis on.
        """
        pass


def get_oob_provider(provider_name, config):
    mgr = driver.DriverManager(
        namespace='teeth_overlord.out_of_band.providers',
        name=provider_name,
        invoke_on_load=True,
        invoke_args=[config],
    )
    return mgr.driver
