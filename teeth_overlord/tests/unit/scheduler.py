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

from teeth_overlord import errors
from teeth_overlord import models
from teeth_overlord import scheduler
from teeth_overlord import tests


class TestInstanceScheduler(tests.TeethMockTestUtilities):

    def setUp(self):
        super(TestInstanceScheduler, self).setUp()

        self.add_mock(models.Instance, 'batch')
        self.add_mock(models.Chassis, 'batch')

        self.scheduler = scheduler.TeethInstanceScheduler()

        self.instance1 = models.Instance(id='instance1',
                                         name='instance1_name',
                                         flavor_id='flavor1',
                                         image_id='image1')

        self.flavorprovider1 = models.FlavorProvider(
            flavor_id='flavor1',
            chassis_model_id='chassismodel1',
            deleted=False)

        self.chassis1 = models.Chassis(
            id='chassis1',
            state=models.ChassisState.READY,
            primary_mac_address='1:2:3:4:5')

    def test_reserve_chassis(self):
        self.add_mock(models.Instance)
        chassis_mock = self.add_mock(models.Chassis,
                                     return_value=[self.chassis1])
        flavor_provider_mock = self.add_mock(
            models.FlavorProvider,
            return_value=[self.flavorprovider1])

        self.scheduler.reserve_chassis(self.instance1, retry=False)

        flavor_provider_mock.assert_called_once_with(
            'filter',
            deleted=False,
            flavor_id=self.instance1.flavor_id)
        chassis_mock.assert_called_once_with(
            'filter',
            state=models.ChassisState.READY)
        chassis_mock.assert_called_once_with(
            'filter',
            chassis_model_id=self.flavorprovider1.chassis_model_id)

        self.assertEqual(self.instance1.chassis_id, self.chassis1.id)
        self.assertEqual(self.instance1.state, models.InstanceState.INACTIVE)
        self.assertEqual(self.chassis1.state, models.ChassisState.BUILD)

        instance_batch_mock = self.get_mock(models.Instance, 'batch')
        self.assertEqual(instance_batch_mock().save.call_count, 1)

        chassis_batch_mock = self.get_mock(models.Chassis, 'batch')
        self.assertEqual(chassis_batch_mock().save.call_count, 1)

    def test_reserve_chassis_already_reserved(self):
        self.chassis1.state = models.ChassisState.ACTIVE
        chassis_mock = self.add_mock(models.Chassis,
                                     return_value=[self.chassis1])
        flavor_provider_mock = self.add_mock(
            models.FlavorProvider,
            return_value=[self.flavorprovider1])

        self.assertRaises(errors.ChassisAlreadyReservedError,
                          self.scheduler.reserve_chassis,
                          self.instance1,
                          retry=False)
        flavor_provider_mock.assert_called_once_with(
            'filter',
            deleted=False,
            flavor_id=self.instance1.flavor_id)
        chassis_mock.assert_called_once_with(
            'filter',
            state=models.ChassisState.READY)
        chassis_mock.assert_called_once_with(
            'filter',
            chassis_model_id=self.flavorprovider1.chassis_model_id)

    def test_reserve_chassis_no_capacity(self):
        flavor_provider_mock = self.add_mock(models.FlavorProvider,
                                             return_value=[])

        self.assertRaises(errors.InsufficientCapacityError,
                          self.scheduler.reserve_chassis,
                          self.instance1,
                          retry=False)
        flavor_provider_mock.assert_called_once_with(
            'filter',
            deleted=False,
            flavor_id=self.instance1.flavor_id)
