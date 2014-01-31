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
import uuid

import structlog


class BaseAgentClient(object):
    """Client for interacting with agents.

    Users of this client call :meth:`get_agent` to get an agent object,
    then call other methods on this class, passing in the agent as well
    as any method-specific parameters.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        self.config = config
        self.log = structlog.get_logger()

    def new_task_id(self):
        """Generate a serialized UUID for use as a task ID."""
        return str(uuid.uuid4())

    @abc.abstractmethod
    def get_agent(self, chassis):
        """Retrieve an agent for the specified Chassis."""
        raise NotImplementedError

    @abc.abstractmethod
    def cache_image(self, agent, image_id):
        """Attempt to cache the specified image."""
        raise NotImplementedError

    @abc.abstractmethod
    def prepare_image(self, agent, image_info, metadata, files):
        """Call the `prepare_image` method on the agent."""
        raise NotImplementedError

    @abc.abstractmethod
    def run_image(self, agent, image_id):
        """Run the specified image."""
        raise NotImplementedError

    @abc.abstractmethod
    def secure_drives(self, agent, drives, key):
        """Secures given drives with given key."""
        raise NotImplementedError

    @abc.abstractmethod
    def erase_drives(self, agent, drives, key):
        """Erases given drives."""
        raise NotImplementedError
