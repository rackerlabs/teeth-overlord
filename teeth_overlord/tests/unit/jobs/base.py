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

import mock
import statsd
import structlog

from teeth_overlord.agent_client import fake as agent_fake
from teeth_overlord import config
from teeth_overlord.images import fake as image_fake
from teeth_overlord.jobs import base as jobs_base
from teeth_overlord import marconi
from teeth_overlord.oob import fake as oob_fake
from teeth_overlord import scheduler


class MockJobExecutor(jobs_base.JobExecutor):
    def __init__(self):
        self.config = config.Config()
        self.log = structlog.get_logger()
        self.agent_client = mock.Mock(spec=agent_fake.FakeAgentClient)
        self.job_client = mock.Mock(spec=jobs_base.JobClient)
        self.image_provider = image_fake.FakeImageProvider(config)
        self.oob_provider = oob_fake.FakeOutOfBandProvider(config)
        self.scheduler = mock.Mock(spec=scheduler.TeethInstanceScheduler)
        self.queue = mock.Mock(spec=marconi.MarconiClient)
        self.stats_client = mock.Mock(spec=statsd.StatsClient)
        self._job_type_cache = {}
