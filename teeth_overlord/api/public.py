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

from teeth_rest.component import APIComponent, APIServer
from teeth_rest.responses import OKResponse, CreatedResponse

from teeth_overlord import models, jobs, errors
from teeth_overlord.images.base import get_image_provider


def _validate_relation(instance, field_name, cls):
    id = getattr(instance, field_name)

    try:
        return cls.get(id=id)
    except cls.DoesNotExist:
        msg = 'Invalid {field_name}, no such {type_name}.'.format(field_name=field_name,
                                                                  type_name=cls.__name__)
        raise errors.InvalidContentError(msg)


class TeethPublicAPI(APIComponent):
    """
    The primary Teeth Overlord API.
    """
    def __init__(self, config):
        super(TeethPublicAPI, self).__init__()
        self.config = config
        self.job_client = jobs.JobClient(config)
        self.image_provider = get_image_provider(config.IMAGE_PROVIDER, config.IMAGE_PROVIDER_CONFIG)

    def add_routes(self):
        """
        Called during initialization. Override to map relative routes to methods.
        """
        # ChassisModel Handlers
        self.route('GET', '/chassis_models', self.list_chassis_models)
        self.route('POST', '/chassis_models', self.create_chassis_model)
        self.route('GET', '/chassis_models/<uuid:chassis_model_id>', self.fetch_chassis_model)

        # Flavor Handlers
        self.route('GET', '/flavors', self.list_flavors)
        self.route('POST', '/flavors', self.create_flavor)
        self.route('GET', '/flavors/<uuid:flavor_id>', self.fetch_flavor)

        # FlavorProvider Handlers
        self.route('GET', '/flavor_providers', self.list_flavor_providers)
        self.route('POST', '/flavor_providers', self.create_flavor_provider)
        self.route('GET', '/flavor_providers/<uuid:flavor_provider_id>', self.fetch_flavor_provider)

        # Chassis Handlers
        self.route('GET', '/chassis', self.list_chassis)
        self.route('POST', '/chassis', self.create_chassis)
        self.route('GET', '/chassis/<uuid:chassis_id>', self.fetch_chassis)

        # Instance Handlers
        self.route('GET', '/instances', self.list_instances)
        self.route('POST', '/instances', self.create_instance)
        self.route('GET', '/instances/<uuid:instance_id>', self.fetch_instance)

    def _crud_list(self, request, cls):
        return OKResponse(list(cls.objects.all()))

    def _crud_fetch(self, request, cls, id):
        try:

            return OKResponse(cls.get(id=id))
        except cls.DoesNotExist:
            raise errors.RequestedObjectNotFoundError(cls, id)

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
        chassis_model = models.ChassisModel.deserialize(self.parse_content(request))
        chassis_model.save()
        return CreatedResponse(request, self.fetch_chassis_model, {'chassis_model_id': chassis_model.id})

    def list_chassis_models(self, request):
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

    def fetch_chassis_model(self, request, chassis_model_id):
        """
        Retrive a ChassisModel. Example::

            {
                "id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                "name": "Supermicro  1027R-WRFT+"
            }

        Returns 200 along with the requested ChassisModels upon success.
        """
        return self._crud_fetch(request, models.ChassisModel, chassis_model_id)

    def create_flavor(self, request):
        """
        Create a Flavor. Example::

            {
                "name": "Extra Fast Server",
            }

        Returns 201 with a Location header upon success.
        """
        flavor = models.Flavor.deserialize(self.parse_content(request))
        flavor.save()
        return self.return_created(request, '/v1.0/flavor/' + str(flavor.id))

    def list_flavors(self, request):
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

    def fetch_flavor(self, request, flavor_id):
        """
        Retrive a Flavor. Example::

            {
                "id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "name": "Extra Fast Server"
            }

        Returns 200 along with the requested Flavors upon success.
        """
        return self._crud_fetch(request, models.Flavor, flavor_id)

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
        flavor_provider = models.FlavorProvider.deserialize(self.parse_content(request))

        _validate_relation(flavor_provider, 'chassis_model_id', models.ChassisModel)
        _validate_relation(flavor_provider, 'flavor_id', models.Flavor)

        flavor_provider.save()
        return self.return_created(request, '/v1.0/flavor_provider/' + str(flavor_provider.id))

    def list_flavor_providers(self, request):
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

    def fetch_flavor_provider(self, request, flavor_provider_id):
        """
        Retrive a FlavorProvider. Example::

            {
                "id": "e5061fd0-371b-46ca-b07b-f415f92eb04f",
                "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "chassis_model_id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                "schedule_priority": 100
            }

        Returns 200 along with the requested FlavorProviders upon success.
        """
        return self._crud_fetch(request, models.FlavorProvider, flavor_provider_id)

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
        chassis = models.Chassis.deserialize(self.parse_content(request))
        chassis_model = _validate_relation(chassis, 'chassis_model_id', models.ChassisModel)
        chassis.ipmi_username = chassis_model.ipmi_default_username
        chassis.ipmi_password = chassis_model.ipmi_default_password
        chassis.save()

        return self.return_created(request, '/v1.0/chassis/' + str(chassis.id))

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

    def fetch_chassis(self, request, chassis_id):
        """
        Retrive a Chassis. Example::

            {
                "id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "name": "Extra Fast Server"
            }

        Returns 200 along with the requested Chassiss upon success.
        """
        return self._crud_fetch(request, models.Chassis, chassis_id)

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
        instance = models.Instance.deserialize(self.parse_content(request))

        # Validate the image ID
        self.image_provider.get_image_info(instance.image_id)

        _validate_relation(instance, 'flavor_id', models.Flavor)
        instance.save()
        self.job_client.submit_job(jobs.CreateInstance, instance_id=str(instance.id))
        return self.return_created(request, '/v1.0/instances/' + str(instance.id))

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


class TeethPublicAPIServer(APIServer):
    """
    Server for the teeth overlord API.
    """

    def __init__(self, config):
        super(TeethPublicAPIServer, self).__init__()
        self.config = config
        self.add_component('/v1.0', TeethPublicAPI(self.config))
