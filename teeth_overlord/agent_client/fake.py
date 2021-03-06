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

from teeth_overlord.agent_client import base


class FakeAgentClient(base.BaseAgentClient):
    """A client that fakes interaction with agents."""

    def get_agent(self, chassis):
        """Retrieve an agent for the specified Chassis."""
        return None

    def cache_image(self, agent, image_id):
        """Attempt to cache the specified image."""
        return

    def prepare_image(self, agent, image_info, metadata, files):
        """Call the `prepare_image` method on the agent."""
        return

    def run_image(self, agent, image_id):
        """Run the specified image."""
        return

    def secure_drives(self, agent, drives, key):
        """Secures given drives with given key."""
        pass

    def erase_drives(self, agent, drives, key):
        """Erases given drives."""
        pass
