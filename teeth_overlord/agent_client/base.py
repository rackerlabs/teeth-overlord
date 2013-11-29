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
from uuid import uuid4


class BaseAgentClient(object):
    """
    Client for interacting with agents.

    Users of this client call :meth:`get_agent_connection` to locate a
    connection made by the agent to an endpoint, then call other methods
    on this class, passing in the agent connection as well as any
    method-specific parameters.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, config):
        self.config = config

    def new_task_id(self):
        """
        Generate a serialized UUID for use as a task ID.
        """
        return str(uuid4())

    @abc.abstractmethod
    def get_agent_connection(self, chassis):
        """
        Retrieve an agent connection for the specified Chassis.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def cache_images(self, connection, image_ids):
        """
        Attempt to cache the specified images. Images are specified in
        priority order, and may not all be cached.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def prepare_image(self, connection, image_id):
        """
        Call the `prepare_image` method on the agent.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def run_image(self, connection, image_id):
        """
        Run the specified image.
        """
        raise NotImplementedError
