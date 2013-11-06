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

from random import choice

from twisted.internet import defer, threads
from cqlengine import BatchQuery
from structlog import get_logger

from teeth_overlord.models import Chassis, ChassisState, InstanceState, FlavorProvider
from teeth_overlord import errors


class TeethInstanceScheduler(object):
    """
    Schedule instances onto chassis.
    """
    def __init__(self, lock_manager):
        self.lock_manager = lock_manager
        self.log = get_logger()

    def reserve_chassis(self, instance):
        """
        Locate and reserve a chassis for the specified instance.
        """
        d = defer.Deferred()

        def _on_failure(failure):
            if failure.check(errors.ChassisAlreadyReservedError):
                _attempt_reservation()
            else:
                d.errback(failure)

        def _attempt_reservation():
            d1 = self._retrieve_eligible_chassis(instance)
            d1.addCallback(self._mark_chassis_reserved, instance)
            d1.addCallbacks(d.callback, _on_failure)

        _attempt_reservation()

        return d

    def _retrieve_eligible_chassis(self, instance):
        """
        Retrieve an available Chassis suitable for the instance.
        """
        d = self._find_flavor_providers(instance)
        d.addCallback(self._find_chassis_for_flavor_providers)
        return d

    def _find_flavor_providers(self, instance):
        """
        Retrieve FlavorProviders in order to determine which ChassisModels are
        capable of providing the requested flavor.
        """
        flavor_provider_query = FlavorProvider.objects.filter(flavor_id=instance.flavor_id)
        return threads.deferToThread(list, flavor_provider_query)

    def _find_chassis_for_flavor_providers(self, flavor_providers):
        """
        Retrieve a Chassis capable of providing the requested flavor.
        """
        d = defer.Deferred()

        # Choose the highest priority flavor provider
        flavor_providers = sorted(flavor_providers,
                                  key=lambda flavor_provider: flavor_provider.schedule_priority,
                                  reverse=True)

        def _with_chassis_list(chassis_list, flavor_providers):
            if len(chassis_list) > 0:
                d.callback(choice(chassis_list))
                return

            _retrieve_chassis_list(flavor_providers[1:])

        def _retrieve_chassis_list(flavor_providers):
            if len(flavor_providers) == 0:
                d.errback(errors.InsufficientCapacityError())
                return

            flavor_provider = flavor_providers[0]

            ready_query = Chassis.objects.filter(state=ChassisState.READY)
            ready_query = ready_query.filter(chassis_model_id=flavor_provider.chassis_model_id)
            ready_query = ready_query.allow_filtering()

            d1 = threads.deferToThread(list, ready_query)
            d1.addCallbacks(_with_chassis_list, d.errback, [flavor_providers])

        _retrieve_chassis_list(flavor_providers)
        return d

    def _mark_chassis_reserved(self, chassis, instance):
        """
        Mark the selected chassis as belonging to this instance, and
        put it into a `BUILD` state.
        """

        def _refetch_chassis(lock):
            refetch_query = Chassis.objects.filter(id=chassis.id)
            return threads.deferToThread(refetch_query.get).addCallback(lambda result: (chassis, lock))

        def _save_chassis_and_instance((chassis, lock)):
            if chassis.state != ChassisState.READY:
                return defer.fail(errors.ChassisAlreadyReservedError(chassis))

            batch = BatchQuery()
            instance.chassis_id = chassis.id
            instance.state = InstanceState.BUILD
            instance.batch(batch).save()
            chassis.state = ChassisState.BUILD
            chassis.batch(batch).save()
            return threads.deferToThread(batch.execute).addCallback(lambda result: (chassis, lock))

        def _unlock((chassis, lock)):
            return lock.release().addCallback(lambda result: chassis)

        d = self.lock_manager.lock('/chassis/{chassis_id}'.format(chassis_id=str(chassis.id)))
        d.addCallback(_refetch_chassis)
        d.addCallback(_save_chassis_and_instance)
        d.addCallback(_unlock)
        return d