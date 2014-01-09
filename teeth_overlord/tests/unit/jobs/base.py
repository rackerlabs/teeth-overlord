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
from teeth_overlord import models
from teeth_overlord.oob import fake as oob_fake
from teeth_overlord import scheduler
from teeth_overlord import tests


class MockJobExecutor(jobs_base.JobExecutor):
    """Job executor with nearly all attributes mocked out."""
    def __init__(self):
        self.config = config.Config()
        self.log = structlog.get_logger()
        self.agent_client = mock.Mock(spec=agent_fake.FakeAgentClient)
        self.job_client = mock.Mock(spec=jobs_base.JobClient)
        self.image_provider = mock.Mock(spec=image_fake.FakeImageProvider)
        self.oob_provider = mock.Mock(spec=oob_fake.FakeOutOfBandProvider)
        self.scheduler = mock.Mock(spec=scheduler.TeethInstanceScheduler)
        self.queue = mock.Mock(spec=marconi.MarconiClient)
        self.stats_client = mock.Mock(spec=statsd.StatsClient)
        self._job_type_cache = {}


class TestJobClient(tests.TeethMockTestUtilities):
    def setUp(self):
        super(TestJobClient, self).setUp()
        self.job_request_mock = self.add_mock(models.JobRequest)
        self.instance_mock = self.add_mock(models.Instance)
        self.job_client = jobs_base.JobClient(self.config)
        self.job_client.queue = mock.Mock(spec=marconi.MarconiClient)

        self.instance = models.Instance(id='test_instance',
                                        name='test_instance',
                                        flavor_id='flavor',
                                        image_id='image',
                                        job_id='test_job')
        self.instance_mock.return_value = [self.instance]

    def test_submit_instance_job(self):
        job = models.JobRequest(id='test_job',
                                job_type='instances.create',
                                params={'instance_id': 'test_instance'})
        self.job_request_mock.return_value = [job]
        self.job_client.submit_job(job.job_type, **job.params)

        job_save = self.get_mock(models.JobRequest, 'save')
        self.assertEqual(job_save.call_count, 1)

        instance_save = self.get_mock(models.Instance, 'save')
        self.assertEqual(instance_save.call_count, 1)

        push_message = self.job_client.queue.push_message
        self.assertEqual(push_message.call_count, 1)

    def test_submit_chassis_job(self):
        job = models.JobRequest(id='test_job',
                                job_type='chassis.decommission',
                                params={'chassis_id': 'test_chassis'})
        self.job_request_mock.return_value = [job]
        self.job_client.submit_job(job.job_type, **job.params)

        job_save = self.get_mock(models.JobRequest, 'save')
        self.assertEqual(job_save.call_count, 1)

        instance_save = self.get_mock(models.Instance, 'save')
        self.assertEqual(instance_save.call_count, 0)

        push_message = self.job_client.queue.push_message
        self.assertEqual(push_message.call_count, 1)
