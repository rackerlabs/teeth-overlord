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
        self.h2c_objects_mock = self.add_mock(models.HardwareToChassis)

        self.add_mock(models.Instance, 'batch')
        self.add_mock(models.Chassis, 'batch')

        self.instance = models.Instance(id='test_instance',
                                        state=models.InstanceState.INACTIVE,
                                        name='instance',
                                        flavor_id='flavor_id',
                                        image_id='image_id',
                                        network_ids=['network_id'])
        self.chassis = models.Chassis(id='test_chassis',
                                      instance_id=None,
                                      state=models.ChassisState.READY,
                                      chassis_model_id='chassis_model_id')
        self.mac = models.HardwareToChassis(hardware_type='mac_address',
                                            hardware_id='1:2:3:4:5:6',
                                            chassis_id='test_chassis')
        request_params = {
            'instance_id': 'test_instance',
            'metadata': {'admin_pass': 'password'},
            'files': {}
        }
        self.job_request = models.JobRequest(id='test_request',
                                             job_type='instances.create',
                                             params=request_params)

        self.instance_objects_mock.return_value = [self.instance]
        self.chassis_objects_mock.return_value = [self.chassis]
        self.h2c_objects_mock.return_value = [self.mac]

        self.executor = jobs_tests_base.MockJobExecutor()
        self.message = {
            'ttl': 1200,
            'body': {'job_request_id': 'test_request'}
        }
        self.job = instance_jobs.CreateInstance(self.executor,
                                                self.job_request,
                                                self.message,
                                                self.config)

        client = self.executor.agent_client
        client.get_agent.return_value = None
        scheduler = self.executor.scheduler
        scheduler.reserve_chassis.return_value = self.chassis

    def _did_prepare_and_run_image(self):
        image_info = self.executor.image_provider.get_image_info('image_id')
        client = self.executor.agent_client
        agent = None
        metadata = self.job_request.params.get('metadata')
        files = self.job_request.params.get('files')

        client.get_agent.assert_called_once_with(self.chassis)
        client.prepare_image.assert_called_once_with(agent,
                                                     image_info,
                                                     metadata,
                                                     files)
        client.run_image.assert_called_once_with(agent, image_info)

    def _did_attach_networks(self):
        self.executor.network_provider.attach.assert_called_once_with(
            self.mac.hardware_id,
            list(self.instance.network_ids)[0]
        )

    def test_prepare_and_run_image(self):
        image_info = self.executor.image_provider.get_image_info('image_id')
        metadata = self.job_request.params.get('metadata')
        files = self.job_request.params.get('files')

        self.job.prepare_and_run_image(self.instance,
                                       self.chassis,
                                       image_info,
                                       metadata,
                                       files)
        self._did_prepare_and_run_image()

    def _instance_is_marked_active(self):
        instance_batch_mock = self.get_mock(models.Instance, 'batch')
        self.assertEqual(instance_batch_mock().save.call_count, 1)
        self.assertEqual(self.instance.state, models.InstanceState.ACTIVE)

    def _chassis_is_marked_active(self):
        chassis_batch_mock = self.get_mock(models.Chassis, 'batch')
        self.assertEqual(chassis_batch_mock().save.call_count, 1)
        self.assertEqual(self.chassis.state, models.ChassisState.ACTIVE)
        self.assertEqual(self.chassis.instance_id, self.instance.id)

    def test_mark_active(self):
        self.job.mark_active(self.instance, self.chassis)
        self._instance_is_marked_active()
        self._chassis_is_marked_active()

    def test_instance_create_job(self):
        scheduler = self.executor.scheduler
        self.job._execute()
        scheduler.reserve_chassis.assert_called_once_with(self.instance)
        self._did_prepare_and_run_image()
        self._instance_is_marked_active()
        self._did_attach_networks()


class DeleteInstanceTestCase(tests.TeethAPITestCase):
    def setUp(self):
        super(DeleteInstanceTestCase, self).setUp()

        self.instance_objects_mock = self.add_mock(models.Instance)
        self.chassis_objects_mock = self.add_mock(models.Chassis)

        self.add_mock(models.Instance, 'batch')
        self.add_mock(models.Chassis, 'batch')

        self.instance = models.Instance(id='test_instance',
                                        state=models.InstanceState.ACTIVE,
                                        name='instance',
                                        chassis_id='test_chassis',
                                        flavor_id='flavor_id',
                                        image_id='image_id')
        self.chassis = models.Chassis(id='test_chassis',
                                      instance_id='test_instance',
                                      state=models.ChassisState.ACTIVE,
                                      chassis_model_id='chassis_model_id')
        request_params = {'instance_id': 'test_instance'}
        self.job_request = models.JobRequest(id='test_request',
                                             job_type='instances.delete',
                                             params=request_params)

        self.instance_objects_mock.return_value = [self.instance]
        self.chassis_objects_mock.return_value = [self.chassis]

        self.executor = jobs_tests_base.MockJobExecutor()
        self.message = {
            'ttl': 1200,
            'body': {'job_request_id': 'test_request'}
        }
        self.job = instance_jobs.DeleteInstance(self.executor,
                                                self.job_request,
                                                self.message,
                                                self.config)

    def test_instance_delete_job(self):
        self.job._execute()

        instance_batch_mock = self.get_mock(models.Instance, 'batch')
        self.assertEqual(self.instance.state, models.InstanceState.DELETED)
        self.assertEqual(instance_batch_mock().save.call_count, 1)

        chassis_batch_mock = self.get_mock(models.Chassis, 'batch')
        self.assertEqual(self.chassis.state, models.ChassisState.CLEAN)
        self.assertEqual(chassis_batch_mock().save.call_count, 1)

        oob = self.executor.oob_provider
        oob.power_chassis_off.assert_called_once_with(self.chassis)

        job_client = self.executor.job_client
        job_client.submit_job.assert_called_once_with(
            'chassis.decommission',
            chassis_id=self.chassis.id)
