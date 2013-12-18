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

from cqlengine import Token

from teeth_rest.component import APIComponent, APIServer
from teeth_rest.responses import (
    ItemResponse,
    PaginatedResponse,
    CreatedResponse,
    DeletedResponse,
)

from teeth_overlord import models, errors
from teeth_overlord.jobs.base import JobClient
from teeth_overlord.images.base import get_image_provider
from teeth_overlord.stats import get_stats_client


DEFAULT_LIMIT = 100


def _validate_relation(instance, field_name, cls):
    id = getattr(instance, field_name)

    try:
        return cls.get(id=id)
    except cls.DoesNotExist:
        msg = 'Invalid {field_name}, no such {type_name}.'.format(field_name=field_name,
                                                                  type_name=cls.__name__)
        raise errors.InvalidContentError(msg)


def _get_single_param(request, param):
    values = request.args.getlist(param)

    if len(values) == 0:
        return None
    if len(values) == 1:
        return values[0]

    msg = 'Multiple \'{param}\' query parameters were provided.'.format(param=param)
    raise errors.InvalidParametersError(msg)


def _get_marker(request):
    return _get_single_param(request, 'marker')


def _get_limit(request):
    limit = _get_single_param(request, 'limit')

    if limit is None:
        return DEFAULT_LIMIT

    try:
        limit = int(limit)
        if limit <= 0:
            raise errors.InvalidParametersError('The \'limit\' query parameter must be greater than 0.')
        return limit
    except ValueError:
        msg = 'The provided \'limit\' query parameter was was not an integer.'
        raise errors.InvalidParametersError(msg)


class TeethPublicAPI(APIComponent):
    """
    The primary Teeth Overlord API.
    """
    def __init__(self, config):
        super(TeethPublicAPI, self).__init__()
        self.config = config
        self.job_client = JobClient(config)
        self.image_provider = get_image_provider(config)
        self.stats_client = get_stats_client(config)

    def add_routes(self):
        """
        Called during initialization. Override to map relative routes to methods.
        """
        # ChassisModel Handlers
        self.route('GET', '/chassis_models', self.list_chassis_models)
        self.route('POST', '/chassis_models', self.create_chassis_model)
        self.route('GET', '/chassis_models/<string:chassis_model_id>', self.fetch_chassis_model)

        # Flavor Handlers
        self.route('GET', '/flavors', self.list_flavors)
        self.route('POST', '/flavors', self.create_flavor)
        self.route('GET', '/flavors/<string:flavor_id>', self.fetch_flavor)

        # FlavorProvider Handlers
        self.route('GET', '/flavor_providers', self.list_flavor_providers)
        self.route('POST', '/flavor_providers', self.create_flavor_provider)
        self.route('GET', '/flavor_providers/<string:flavor_provider_id>', self.fetch_flavor_provider)

        # Chassis Handlers
        self.route('GET', '/chassis', self.list_chassis)
        self.route('POST', '/chassis', self.create_chassis)
        self.route('GET', '/chassis/<string:chassis_id>', self.fetch_chassis)

        # Instance Handlers
        self.route('GET', '/instances', self.list_instances)
        self.route('POST', '/instances', self.create_instance)
        self.route('GET', '/instances/<string:instance_id>', self.fetch_instance)
        self.route('DELETE', '/instances/<string:instance_id>', self.delete_instance)

    def _crud_list(self, request, query, list_method):
        marker = _get_marker(request)
        limit = _get_limit(request)
        query = query.limit(limit)

        if marker:
            query = query.filter(pk__token__gt=Token(marker))

        items = list(query)

        if len(items) == limit:
            # limit must be >= 1, so items[] is never empty
            marker = items[-1].id
        else:
            marker = None

        return PaginatedResponse(request, items, list_method, marker, limit)

    def _crud_fetch(self, request, cls, id):
        try:
            return ItemResponse(cls.get(id=id))
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

        self.stats_client.incr('chassis_models.create')
        return CreatedResponse(request, self.fetch_chassis_model, {'chassis_model_id': chassis_model.id})

    def list_chassis_models(self, request):
        """
        List ChassisModels. Example::

            {
                "items": [
                    {
                        "id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                        "name": "Supermicro  1027R-WRFT+"
                    }
                ],
                "links": [
                    {
                        "href": "http://localhost:8080/v1.0/chassis_models?
                                    marker=e0d4774b-daa6-4361-b4d9-ab367e40d885&limit=1",
                        "rel": "next"
                    }
                ]
            }

        Returns 200 along with a list of ChassisModels upon success.
        """
        self.stats_client.incr('chassis_models.list')
        return self._crud_list(request, models.ChassisModel.objects, self.list_chassis_models)

    def fetch_chassis_model(self, request, chassis_model_id):
        """
        Retrive a ChassisModel. Example::

            {
                "id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                "name": "Supermicro  1027R-WRFT+"
            }

        Returns 200 along with the requested ChassisModels upon success.
        """
        self.stats_client.incr('chassis_models.fetch')
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

        self.stats_client.incr('flavors.create')
        return CreatedResponse(request, self.fetch_flavor, {'flavor_id': flavor.id})

    def list_flavors(self, request):
        """
        List Flavors. Example::

            {
                "items": [
                    {
                        "id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                        "name": "Extra Fast Server"
                    }
                ],
                "links": [
                    {
                        "href": "http://localhost:8080/v1.0/flavors?
                                    marker=d5942a92-ac78-49f6-95c8-d837cfd1f8d2&limit=1",
                        "rel": "next"
                    }
                ]
            }

        Returns 200 with a list of Flavors upon success.
        """
        self.stats_client.incr('flavors.list')
        return self._crud_list(request, models.Flavor.objects, self.list_flavors)

    def fetch_flavor(self, request, flavor_id):
        """
        Retrive a Flavor. Example::

            {
                "id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "name": "Extra Fast Server"
            }

        Returns 200 along with the requested Flavors upon success.
        """
        self.stats_client.incr('flavors.fetch')
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

        self.stats_client.incr('flavor_providers.create')
        return CreatedResponse(request, self.fetch_flavor_provider, {
            'flavor_provider_id': flavor_provider.id
        })

    def list_flavor_providers(self, request):
        """
        List FlavorProviders. Example::

            {
                "items": [
                    {
                        "id": "e5061fd0-371b-46ca-b07b-f415f92eb04f",
                        "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                        "chassis_model_id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                        "schedule_priority": 100
                    }
                ],
                "links": [
                    {
                        "href": "http://localhost:8080/v1.0/flavor_providers?
                                    marker=e0d4774b-daa6-4361-b4d9-ab367e40d885&limit=1",
                        "rel": "next"
                    }
                ]
            }

        Returns 200 with a list of FlavorProviders upon success.
        """
        self.stats_client.incr('flavor_providers.list')
        return self._crud_list(request, models.FlavorProvider.objects, self.list_flavor_providers)

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
        self.stats_client.incr('flavor_providers.fetch')
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

        self.stats_client.incr('chassis.create')
        return CreatedResponse(request, self.fetch_chassis, {'chassis_id': chassis.id})

    def list_chassis(self, request):
        """
        List Chassis. Example::

            {
                "items": [
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
                ],
                "links": [
                    {
                        "href": "http://localhost:8080/v1.0/chassis?
                                    marker=e2c328c7-fcb5-4989-8bbd-bdd5877dc219&limit=3",
                        "rel": "next"
                    }
                ]
            }

        Returns 200 with a list of Chassis upon success.
        """
        self.stats_client.incr('chassis.list')
        return self._crud_list(request, models.Chassis.objects, self.list_chassis)

    def fetch_chassis(self, request, chassis_id):
        """
        Retrive a Chassis. Example::

            {
                "id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "name": "Extra Fast Server"
            }

        Returns 200 along with the requested Chassiss upon success.
        """
        self.stats_client.incr('chassis.fetch')
        return self._crud_fetch(request, models.Chassis, chassis_id)

    def create_instance(self, request):
        """
        Create an Instance. Example::

            {
                "name": "web0",
                "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "image_id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f"
            }

        Returns 201 with a Location header upon success.
        """
        instance = models.Instance.deserialize(self.parse_content(request))

        # Validate the image ID
        self.image_provider.get_image_info(instance.image_id)

        _validate_relation(instance, 'flavor_id', models.Flavor)
        instance.save()
        self.job_client.submit_job('instances.create',
                                   instance_id=instance.id)

        self.stats_client.incr('instances.request_create')
        return CreatedResponse(request, self.fetch_instance, {
            'instance_id': instance.id,
        })

    def list_instances(self, request):
        """
        List Instances. Example::

            {
                "items": [
                    {
                        "id": "e7269c27-abd8-49f1-ba8a-ac063f61bd65",
                        "name": "Test Instance B",
                        "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                        "chassis_id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f",
                        "state": "ACTIVE"
                    },
                    {
                        "id": "f002190f-522b-4a0a-95ee-8fe72824de7a",
                        "name": "Test Instance C",
                        "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                        "chassis_id": "3ddee7bd-7a35-489b-bf5d-54fd8f09496c",
                        "state": "BUILD"
                    }
                ],
                "links": []
            }

        Returns 200 with a list of Instances upon success.
        """
        self.stats_client.incr('instances.list')
        return self._crud_list(request, models.Instance.objects, self.list_instances)

    def fetch_instance(self, request, instance_id):
        """
        Retrieve an instance. Example::

            {
                "id": "e7269c27-abd8-49f1-ba8a-ac063f61bd65",
                "name": "Test Instance B",
                "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "chassis_id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f",
                "state": "ACTIVE"
            }

        Returns 200 with the requested Instance upon success.
        """
        self.stats_client.incr('instances.fetch')
        return self._crud_fetch(request, models.Instance, instance_id)

    def delete_instance(self, request, instance_id):
        try:
            instance = models.Instance.objects.get(id=instance_id)
        except models.Instance.NotFound:
            raise errors.RequestedObjectNotFoundError(models.Instance, instance_id)

        if instance.state in (models.InstanceState.DELETING, models.InstanceState.DELETED):
            raise errors.ObjectAlreadyDeletedError(models.Instance, instance_id)

        instance.state = models.InstanceState.DELETING
        instance.save()

        self.job_client.submit_job('instances.delete',
                                   instance_id=instance.id)

        self.stats_client.incr('instances.request_delete')
        return DeletedResponse()


class TeethPublicAPIServer(APIServer):
    """
    Server for the teeth overlord API.
    """

    def __init__(self, config):
        super(TeethPublicAPIServer, self).__init__()
        self.config = config
        self.add_component('/v1.0', TeethPublicAPI(self.config))
