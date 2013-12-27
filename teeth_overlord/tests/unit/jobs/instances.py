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

from teeth_overlord.jobs import instances as instance_jobs
from teeth_overlord import models
from teeth_overlord import tests
from teeth_overlord.tests.unit.jobs import base as jobs_tests_base


class CreateInstanceTestCase(tests.TeethAPITestCase):
    def setUp(self):
        super(CreateInstanceTestCase, self).setUp()

        self.instance_objects_mock = self.add_mock(models.Instance)
        self.chassis_objects_mock = self.add_mock(models.Chassis)
        self.job_request_objects_mock = self.add_mock(models.JobRequest)

        self.instance = models.Instance(id='test_instance',
                                        state=models.InstanceState.BUILD,
                                        name='instance',
                                        flavor_id='flavor_id',
                                        image_id='image_id')
        self.chassis = models.Chassis(id='test_chassis',
                                      instance_id=None,
                                      state=models.ChassisState.READY,
                                      chassis_model_id='chassis_model_id',
                                      primary_mac_address='00:00:00:00:00:00')
        request_params = {'instance_id': 'test_instance'}
        self.job_request = models.JobRequest(id='test_request',
                                             job_type='instances.create',
                                             params=request_params)

        self.executor = jobs_tests_base.MockJobExecutor()
        self.message = {
            'ttl': 1200,
            'body': {'job_request_id': 'test_request'}
        }
        self.job = instance_jobs.CreateInstance(self.executor,
                                                self.job_request,
                                                self.message)

    def _did_prepare_and_run_image(self):
        client = self.executor.agent_client
        client.get_agent_connection.assert_called_once_with(self.chassis)
        client.prepare_image.assert_called_once()
        client.run_image.assert_called_once()

    def test_prepare_and_run_image(self):
        image_info = self.executor.image_provider.get_image_info('image_id')
        self.job.prepare_and_run_image(self.instance, self.chassis, image_info)
        self._did_prepare_and_run_image()

    def _is_marked_active(self):
        self.assertEqual(self.instance.state, models.InstanceState.ACTIVE)
        self.assertEqual(self.chassis.state, models.ChassisState.ACTIVE)
        self.assertEqual(self.chassis.instance_id, self.instance.id)

    def test_mark_active(self):
        self.job.mark_active(self.instance, self.chassis)
        self._is_marked_active()

    def test_instance_create_job(self):
        self.job._execute()
        scheduler = self.executor.scheduler
        scheduler.reserve_chassis.assert_called_once_with(self.instance)
        self._did_prepare_and_run_image()
        self._is_marked_active()
