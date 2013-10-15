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

from klein import Klein
from twisted.internet import threads, defer
from cqlengine.query import DoesNotExist

from teeth_overlord import models, jobs, rest, errors


class TeethAPI(rest.RESTServer):
    """
    The primary Teeth Overlord API.
    """
    app = Klein()

    def __init__(self, config):
        rest.RESTServer.__init__(self, config, config.API_HOST, config.API_PORT)
        self.job_client = jobs.JobClient(config)

    def _crud_list(self, request, cls):
        def _retrieved(objects):
            return self.return_ok(request, objects)

        return threads.deferToThread(list, cls.objects.all()).addCallback(_retrieved)

    def _crud_fetch(self, request, cls, id):
        def _retrieved(obj):
            return self.return_ok(request, obj)

        def _on_failure(failure):
            if failure.check(DoesNotExist):
                raise errors.RequestedObjectNotFoundError(cls, id)
            return failure

        return threads.deferToThread(cls.get, id=id).addCallbacks(_retrieved, _on_failure)

    @app.route('/v1.0/chassis_models', methods=['POST'])
    def create_chassis_model(self, request):
        """
        Create a ChassisModel. Example::

            {
                "name": "Supermicro  1027R-WRFT+",
                "default_impi_username": "ADMIN",
                "default_ipmi_password": "ADMIN"
            }

        Returns 201 with a Location header upon success.
        """
        def _saved(chassis_model):
            return self.return_created(request, '/v1.0/chassis_model/' + str(chassis_model.id))

        chassis_model = models.ChassisModel.deserialize(self.parse_content(request))
        return threads.deferToThread(chassis_model.save).addCallback(_saved)

    @app.route('/v1.0/chassis_models', methods=['GET'])
    def list_chassis_model(self, request):
        """
        List ChassisModels. Example::

            [
                {
                    "id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                    "name": "Supermicro  1027R-WRFT+"
                }
            ]

        Returns 200 along with a list of ChassisModels upon success.
        """
        return self._crud_list(request, models.ChassisModel)

    @app.route('/v1.0/flavors', methods=['POST'])
    def create_flavor(self, request):
        """
        Create a Flavor. Example::

            {
                "name": "Extra Fast Server",
            }

        Returns 201 with a Location header upon success.
        """
        def _saved(flavor):
            return self.return_created(request, '/v1.0/flavor/' + str(flavor.id))

        flavor = models.Flavor.deserialize(self.parse_content(request))
        return threads.deferToThread(flavor.save).addCallback(_saved)

    @app.route('/v1.0/flavors', methods=['GET'])
    def list_flavor(self, request):
        """
        List Flavors. Example::

            [
                {
                    "id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                    "name": "Extra Fast Server"
                }
            ]

        Returns 200 with a list of Flavors upon success.
        """
        return self._crud_list(request, models.Flavor)

    @app.route('/v1.0/flavor_providers', methods=['POST'])
    def create_flavor_provider(self, request):
        """
        Create a FlavorProvider, which maps a Flavor to a ChassisModel. Example::

            {
                "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "chassis_model_id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                "schedule_priority": 100,
            }

        When a user creates an instance, we use FlavorProviders to
        determine which chassis are able to provide the requested
        flavor. When multiple chassis of different models are able
        to provide the same flavor, we will prefer chassis of the
        model which provides the flavor with a higher
        `schedule_priority`.

        Returns 201 with a Location header upon success.
        """
        def _saved(flavor_provider):
            return self.return_created(request, '/v1.0/flavor_provider/' + str(flavor_provider.id))

        def _validated(results):
            return threads.deferToThread(flavor_provider.save).addCallback(_saved)

        flavor_provider = models.FlavorProvider.deserialize(self.parse_content(request))
        d = defer.gatherResults([
            threads.deferToThread(models.ChassisModel.get, id=flavor_provider.chassis_model_id),
            threads.deferToThread(models.Flavor.get, id=flavor_provider.flavor_id),
        ])
        d.addCallback(_validated)
        return d

    @app.route('/v1.0/flavor_providers', methods=['GET'])
    def list_flavor_provider(self, request):
        """
        List FlavorProviders. Example::

            [
                {
                    "id": "e5061fd0-371b-46ca-b07b-f415f92eb04f",
                    "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                    "chassis_model_id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                    "schedule_priority": 100
                }
            ]

        Returns 200 with a list of FlavorProviders upon success.
        """
        return self._crud_list(request, models.FlavorProvider)

    @app.route('/v1.0/chassis', methods=['POST'])
    def create_chassis(self, request):
        """
        Create a Chassis. Example::

            {
                "chassis_model_id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                "primary_mac_address": "bc:76:4e:20:03:5f",
            }

        When we rack and connect a new physical server, this call should
        be used to add it to inventory and bootstrap it to a `READY`
        state.

        TODO: actually bootstrap the chassis to a `READY` state, change
        the passwords, etc.

        Returns 201 with a Location header upon success.
        """
        def _saved(chassis):
            return self.return_created(request, '/v1.0/chassis/' + str(chassis.id))

        def _with_chassis_model(chassis_model, chassis):
            chassis.ipmi_username = chassis_model.ipmi_default_username
            chassis.ipmi_password = chassis_model.ipmi_default_password
            return threads.deferToThread(chassis.save).addCallback(_saved)

        chassis = models.Chassis.deserialize(self.parse_content(request))
        d = threads.deferToThread(models.ChassisModel.objects.get, id=chassis.chassis_model_id)
        d.addCallback(_with_chassis_model, chassis)
        return d

    @app.route('/v1.0/chassis', methods=['GET'])
    def list_chassis(self, request):
        """
        List Chassis. Example::

            [
                {
                    "id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f",
                    "state": "ACTIVE",
                    "chassis_model_id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                    "primary_mac_address": "bc:76:4e:20:03:5f"
                },
                {
                    "id": "3ddee7bd-7a35-489b-bf5d-54fd8f09496c",
                    "state": "BUILD",
                    "chassis_model_id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                    "primary_mac_address": "bc:76:4e:20:12:44"
                },
                {
                    "id": "e2c328c7-fcb5-4989-8bbd-bdd5877dc219",
                    "state": "READY",
                    "chassis_model_id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                    "primary_mac_address": "40:6c:8f:19:14:17"
                }
            ]

        Returns 200 with a list of Chassis upon success.
        """
        return self._crud_list(request, models.Chassis)

    @app.route('/v1.0/instances', methods=['POST'])
    def create_instance(self, request):
        """
        Create an Instance. Example::

            {
                "project_id": "545251",
                "name": "web0",
                "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "image_id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f"
            }

        Note that "project_id" is intended to correspond to an OpenStack
        tenant ID.

        Returns 201 with a Location header upon success.
        """
        def _execute_job(result):
            return self.job_client.submit_job(jobs.CreateInstance, instance_id=str(instance.id))

        def _respond(result):
            return self.return_created(request, '/v1.0/instances/' + str(instance.id))

        instance = models.Instance.deserialize(self.parse_content(request))
        d = threads.deferToThread(instance.save)
        d.addCallback(_execute_job)
        d.addCallback(_respond)
        return d

    @app.route('/v1.0/instances', methods=['GET'])
    def list_instances(self, request):
        """
        List Instances. Example::

            [
                {
                    "id": "e7269c27-abd8-49f1-ba8a-ac063f61bd65",
                    "project_id": "1234567",
                    "name": "Test Instance B",
                    "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                    "chassis_id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f",
                    "state": "ACTIVE"
                },
                {
                    "id": "f002190f-522b-4a0a-95ee-8fe72824de7a",
                    "project_id": "1234567",
                    "name": "Test Instance C",
                    "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                    "chassis_id": "3ddee7bd-7a35-489b-bf5d-54fd8f09496c",
                    "state": "BUILD"
                }
            ]

        Returns 200 with a list of Instances upon success.
        """
        return self._crud_list(request, models.Instance)

    @app.route('/v1.0/instances/<string:instance_id>', methods=['GET'])
    def fetch_instance(self, request, instance_id):
        """
        Retrieve an instance. Example::

            {
                "id": "e7269c27-abd8-49f1-ba8a-ac063f61bd65",
                "project_id": "1234567",
                "name": "Test Instance B",
                "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "chassis_id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f",
                "state": "ACTIVE"
            }

        Returns 200 with the requested Instance upon success.
        """
        return self._crud_fetch(request, models.Instance, instance_id)

    @app.handle_errors
    def return_error(self, request, failure):
        """
        Pass any errors to the parent class's error handler.
        """
        return rest.RESTServer.return_error(self, request, failure)
