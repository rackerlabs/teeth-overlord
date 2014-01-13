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

import cqlengine

from carbide_rest import component
from carbide_rest import errors as rest_errors
from carbide_rest import responses

from carbide_overlord import errors
from carbide_overlord.images import base as images_base
from carbide_overlord.jobs import base as jobs_base
from carbide_overlord import models
from carbide_overlord import stats


DEFAULT_LIMIT = 100


def _get_single_param(request, param):
    values = request.args.getlist(param)

    if len(values) == 0:
        return None
    if len(values) == 1:
        return values[0]

    msg = 'Multiple \'{param}\' query parameters were provided.'.format(
        param=param)
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
            raise errors.InvalidParametersError(
                'The \'limit\' query parameter must be greater than 0.')
        return limit
    except ValueError:
        msg = 'The provided \'limit\' query parameter was was not an integer.'
        raise errors.InvalidParametersError(msg)


class CarbidePublicAPI(component.APIComponent):

    """The primary Carbide Overlord API."""

    def __init__(self, config, job_client=None, stats_client=None):
        super(CarbidePublicAPI, self).__init__()
        self.config = config
        self.job_client = job_client or jobs_base.JobClient(config)
        self.stats_client = stats_client or stats.get_stats_client(
            config,
            prefix='api')
        self.image_provider = images_base.get_image_provider(config)

    def add_routes(self):
        """Called during initialization. Override to map relative routes to
        methods.
        """
        # ChassisModel Handlers
        self.route('GET', '/chassis_models', self.list_chassis_models)
        self.route('POST', '/chassis_models', self.create_chassis_model)
        self.route('GET', '/chassis_models/<string:chassis_model_id>',
                   self.fetch_chassis_model)
        self.route('DELETE', '/chassis_models/<string:chassis_model_id>',
                   self.delete_chassis_model)

        # Flavor Handlers
        self.route('GET', '/flavors', self.list_flavors)
        self.route('POST', '/flavors', self.create_flavor)
        self.route('GET', '/flavors/<string:flavor_id>', self.fetch_flavor)
        self.route('DELETE', '/flavors/<string:flavor_id>', self.delete_flavor)

        # FlavorProvider Handlers
        self.route('GET', '/flavor_providers', self.list_flavor_providers)
        self.route('POST', '/flavor_providers', self.create_flavor_provider)
        self.route('GET', '/flavor_providers/<string:flavor_provider_id>',
                   self.fetch_flavor_provider)
        self.route('DELETE', '/flavor_providers/<string:flavor_provider_id>',
                   self.delete_flavor_provider)

        # Chassis Handlers
        self.route('GET', '/chassis', self.list_chassis)
        self.route('POST', '/chassis', self.create_chassis)
        self.route('GET', '/chassis/<string:chassis_id>', self.fetch_chassis)
        self.route('DELETE', '/chassis/<string:chassis_id>',
                   self.delete_chassis)

        # Instance Handlers
        self.route('GET', '/instances', self.list_instances)
        self.route('POST', '/instances', self.create_instance)
        self.route('GET', '/instances/<string:instance_id>',
                   self.fetch_instance)
        self.route('DELETE', '/instances/<string:instance_id>',
                   self.delete_instance)

    def _validate_relation(self, instance, field_name, cls):
        id = getattr(instance, field_name)

        try:
            model = cls.objects.get(id=id)
        except cls.DoesNotExist:
            msg = 'Invalid {field_name}, no such {type_name}.'.format(
                field_name=field_name,
                type_name=cls.__name__)
            raise rest_errors.InvalidContentError(msg)

        if hasattr(model, "deleted") and model.deleted:
            msg = 'Invalid {field_name}, given {type_name} is deleted.'.format(
                field_name=field_name,
                type_name=cls.__name__)
            raise rest_errors.InvalidContentError(msg)

        return model

    def _crud_list(self, request, cls, list_method):
        marker = _get_marker(request)
        limit = _get_limit(request)
        query = cls.objects.all().limit(limit)

        if marker:
            query = query.filter(pk__token__gt=cqlengine.Token(marker))

        items = list(query)

        if len(items) == limit:
            # limit must be >= 1, so items[] is never empty
            marker = items[-1].id
        else:
            marker = None

        return responses.PaginatedResponse(request,
                                           items,
                                           list_method,
                                           marker,
                                           limit)

    def _crud_fetch(self, request, cls, query):
        try:
            return responses.ItemResponse(query.get())
        except cls.DoesNotExist:
            raise errors.RequestedObjectNotFoundError(cls, id)

    @stats.incr_stat('chassis_models.create')
    def create_chassis_model(self, request):
        """Create a ChassisModel. Example::

            {
                "name": "Supermicro  1027R-WRFT+",
                "default_impi_username": "ADMIN",
                "default_ipmi_password": "ADMIN"
            }

        Returns 201 with a Location header upon success.
        """
        try:
            body = self.parse_content(request)
            chassis_model = models.ChassisModel.deserialize(body)
        except cqlengine.ValidationError as e:
            raise rest_errors.InvalidContentError(e.message)

        chassis_model.save()
        location_params = {'chassis_model_id': chassis_model.id}
        return responses.CreatedResponse(request,
                                         self.fetch_chassis_model,
                                         location_params)

    @stats.incr_stat('chassis_models.list')
    def list_chassis_models(self, request):
        """List ChassisModels. Example::

            {
                "items": [
                    {
                        "id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                        "name": "Supermicro  1027R-WRFT+"
                    }
                ],
                "links": [
                    {
                        "href": "http://localhost:8080/v1/chassis_models?
                                    marker=e0d4774b-daa6-4361-b4d9-ab367e40d885
                                    &limit=1",
                        "rel": "next"
                    }
                ]
            }

        Returns 200 along with a list of ChassisModels upon success.
        """
        return self._crud_list(request,
                               models.ChassisModel,
                               self.list_chassis_models)

    @stats.incr_stat('chassis_models.fetch')
    def fetch_chassis_model(self, request, chassis_model_id):
        """Retrive a ChassisModel. Example::

            {
                "id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                "name": "Supermicro  1027R-WRFT+"
            }

        Returns 200 along with the requested ChassisModels upon success.
        """
        query = models.ChassisModel.filter(id=chassis_model_id)
        return self._crud_fetch(request, models.ChassisModel, query)

    @stats.incr_stat('chassis_models.delete')
    def delete_chassis_model(self, request, chassis_model_id):
        """Delete a ChassisModel.

        Return 204 on success.
        """
        try:
            chassis_model = models.ChassisModel.objects.get(
                id=chassis_model_id)
        except models.ChassisModel.DoesNotExist:
            raise errors.RequestedObjectNotFoundError(models.ChassisModel,
                                                      chassis_model_id)

        if chassis_model.deleted:
            raise errors.ObjectAlreadyDeletedError(models.ChassisModel,
                                                   chassis_model.id)

        flavor_providers_count = (models.FlavorProvider.objects
                                  .allow_filtering()
                                  .filter(deleted=False,
                                          chassis_model_id=chassis_model.id)
                                  .count())

        if flavor_providers_count > 0:
            details = ("ChassisModel is referenced in {count} active "
                       "FlavorProviders").format(count=flavor_providers_count)
            raise errors.ObjectCannotBeDeletedError(models.ChassisModel,
                                                    chassis_model.id,
                                                    details=details)

        chassis_model.deleted = True
        chassis_model.save()

        return responses.DeletedResponse()

    @stats.incr_stat('flavors.create')
    def create_flavor(self, request):
        """Create a Flavor. Example::

            {
                "name": "Extra Fast Server",
            }

        Returns 201 with a Location header upon success.
        """
        try:
            flavor = models.Flavor.deserialize(self.parse_content(request))
        except cqlengine.ValidationError as e:
            raise rest_errors.InvalidContentError(e.message)

        flavor.save()
        return responses.CreatedResponse(request,
                                         self.fetch_flavor,
                                         {'flavor_id': flavor.id})

    @stats.incr_stat('flavors.list')
    def list_flavors(self, request):
        """List Flavors. Example::

            {
                "items": [
                    {
                        "id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                        "name": "Extra Fast Server"
                    }
                ],
                "links": [
                    {
                        "href": "http://localhost:8080/v1/flavors?
                                    marker=d5942a92-ac78-49f6-95c8-d837cfd1f8d2
                                    &limit=1",
                        "rel": "next"
                    }
                ]
            }

        Returns 200 with a list of Flavors upon success.
        """
        return self._crud_list(request, models.Flavor, self.list_flavors)

    @stats.incr_stat('flavors.fetch')
    def fetch_flavor(self, request, flavor_id):
        """Retrive a Flavor. Example::

            {
                "id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "name": "Extra Fast Server"
            }

        Returns 200 along with the requested Flavors upon success.
        """
        query = models.Flavor.objects.filter(id=flavor_id)
        return self._crud_fetch(request, models.Flavor, query)

    @stats.incr_stat('flavors.delete')
    def delete_flavor(self, request, flavor_id):
        """Delete a Flavor.

        Return 204 on success.
        """
        try:
            flavor = models.Flavor.objects.get(id=flavor_id)
        except models.Flavor.DoesNotExist:
            raise errors.RequestedObjectNotFoundError(models.Flavor, flavor_id)

        if flavor.deleted:
            raise errors.ObjectAlreadyDeletedError(models.Flavor, flavor.id)

        flavor_providers_count = (models.FlavorProvider.objects
                                  .allow_filtering()
                                  .filter(deleted=False, flavor_id=flavor.id)
                                  .count())

        if flavor_providers_count > 0:
            details = ("Flavor is referenced in {count} active "
                       "FlavorProviders").format(count=flavor_providers_count)
            raise errors.ObjectCannotBeDeletedError(models.Flavor,
                                                    flavor.id,
                                                    details=details)

        flavor.deleted = True
        flavor.save()

        return responses.DeletedResponse()

    @stats.incr_stat('flavor_providers.create')
    def create_flavor_provider(self, request):
        """Create a FlavorProvider, which maps a Flavor to a ChassisModel.
        Example::

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
        try:
            body = self.parse_content(request)
            flavor_provider = models.FlavorProvider.deserialize(body)
        except cqlengine.ValidationError as e:
            raise rest_errors.InvalidContentError(e.message)

        self._validate_relation(flavor_provider,
                                'chassis_model_id',
                                models.ChassisModel)
        self._validate_relation(flavor_provider, 'flavor_id', models.Flavor)

        flavor_provider.save()
        return responses.CreatedResponse(request, self.fetch_flavor_provider, {
            'flavor_provider_id': flavor_provider.id
        })

    @stats.incr_stat('flavor_providers.list')
    def list_flavor_providers(self, request):
        """List FlavorProviders. Example::

            {
                "items": [
                    {
                        "id": "e5061fd0-371b-46ca-b07b-f415f92eb04f",
                        "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                        "chassis_model_id":
                            "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                        "schedule_priority": 100
                    }
                ],
                "links": [
                    {
                        "href": "http://localhost:8080/v1/flavor_providers?
                                    marker=e0d4774b-daa6-4361-b4d9-ab367e40d885
                                    &limit=1",
                        "rel": "next"
                    }
                ]
            }

        Returns 200 with a list of FlavorProviders upon success.
        """
        return self._crud_list(request,
                               models.FlavorProvider,
                               self.list_flavor_providers)

    @stats.incr_stat('flavor_providers.fetch')
    def fetch_flavor_provider(self, request, flavor_provider_id):
        """Retrive a FlavorProvider. Example::

            {
                "id": "e5061fd0-371b-46ca-b07b-f415f92eb04f",
                "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "chassis_model_id": "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                "schedule_priority": 100
            }

        Returns 200 along with the requested FlavorProviders upon success.
        """
        query = models.FlavorProvider.objects.filter(id=flavor_provider_id)
        return self._crud_fetch(request, models.FlavorProvider, query)

    @stats.incr_stat('flavor_providers.delete')
    def delete_flavor_provider(self, request, flavor_provider_id):
        """Delete a Flavor.

        Return 204 on success.
        """
        try:
            flavor_provider = models.FlavorProvider.objects.get(
                id=flavor_provider_id)
        except models.FlavorProvider.DoesNotExist:
            raise errors.RequestedObjectNotFoundError(models.FlavorProvider,
                                                      flavor_provider_id)

        if flavor_provider.deleted:
            raise errors.ObjectAlreadyDeletedError(models.FlavorProvider,
                                                   flavor_provider.id)

        flavor_provider.deleted = True
        flavor_provider.save()

        return responses.DeletedResponse()

    @stats.incr_stat('chassis.create')
    def create_chassis(self, request):
        """Create a Chassis. Example::

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
        try:
            chassis = models.Chassis.deserialize(self.parse_content(request))
        except cqlengine.ValidationError as e:
            raise rest_errors.InvalidContentError(e.message)

        chassis_model = self._validate_relation(chassis,
                                                'chassis_model_id',
                                                models.ChassisModel)
        chassis.ipmi_username = chassis_model.ipmi_default_username
        chassis.ipmi_password = chassis_model.ipmi_default_password
        chassis.save()

        return responses.CreatedResponse(request,
                                         self.fetch_chassis,
                                         {'chassis_id': chassis.id})

    @stats.incr_stat('chassis.list')
    def list_chassis(self, request):
        """List Chassis. Example::

            {
                "items": [
                    {
                        "id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f",
                        "state": "ACTIVE",
                        "chassis_model_id":
                            "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                        "primary_mac_address": "bc:76:4e:20:03:5f"
                    },
                    {
                        "id": "3ddee7bd-7a35-489b-bf5d-54fd8f09496c",
                        "state": "BUILD",
                        "chassis_model_id":
                            "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                        "primary_mac_address": "bc:76:4e:20:12:44"
                    },
                    {
                        "id": "e2c328c7-fcb5-4989-8bbd-bdd5877dc219",
                        "state": "READY",
                        "chassis_model_id":
                            "e0d4774b-daa6-4361-b4d9-ab367e40d885",
                        "primary_mac_address": "40:6c:8f:19:14:17"
                    }
                ],
                "links": [
                    {
                        "href": "http://localhost:8080/v1/chassis?
                                    marker=e2c328c7-fcb5-4989-8bbd-bdd5877dc219
                                    &limit=3",
                        "rel": "next"
                    }
                ]
            }

        Returns 200 with a list of Chassis upon success.
        """
        return self._crud_list(request, models.Chassis, self.list_chassis)

    @stats.incr_stat('chassis.fetch')
    def fetch_chassis(self, request, chassis_id):
        """Retrive a Chassis. Example::

            {
                "id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "name": "Extra Fast Server"
            }

        Returns 200 along with the requested Chassiss upon success.
        """
        query = models.Chassis.objects.filter(id=chassis_id)
        return self._crud_fetch(request, models.Chassis, query)

    @stats.incr_stat('chassis.delete')
    def delete_chassis(self, request, chassis_id):
        """Delete a chassis.

        Returns 204 on success.
        """
        try:
            chassis = models.Chassis.objects.get(id=chassis_id)
        except models.Chassis.DoesNotExist:
            raise errors.RequestedObjectNotFoundError(models.Chassis,
                                                      chassis_id)

        if chassis.state == models.ChassisState.DELETED:
            raise errors.ObjectAlreadyDeletedError(models.Chassis, chassis.id)

        # if instance_id is None, there are no running instances and the
        # chassis has been cleaned - thus safe to delete.
        if chassis.instance_id is not None:
            msg = "Chassis has a non-empty instance_id"
            raise errors.ObjectCannotBeDeletedError(models.Chassis,
                                                    chassis.id,
                                                    details=msg)

        chassis.state = models.ChassisState.DELETED
        chassis.save()

        return responses.DeletedResponse()

    @stats.incr_stat('instances.request_create')
    def create_instance(self, request):
        """Create an Instance. Example::

            {
                "name": "web0",
                "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "image_id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f"
            }

        Returns 201 with a Location header upon success.
        """
        try:
            instance = models.Instance.deserialize(self.parse_content(request))
        except cqlengine.ValidationError as e:
            raise rest_errors.InvalidContentError(e.message)

        # Validate the image ID
        self.image_provider.get_image_info(instance.image_id)

        self._validate_relation(instance, 'flavor_id', models.Flavor)
        instance.save()
        self.job_client.submit_job('instances.create',
                                   instance_id=instance.id)

        return responses.CreatedResponse(request, self.fetch_instance, {
            'instance_id': instance.id,
        })

    @stats.incr_stat('instances.list')
    def list_instances(self, request):
        """List Instances. Example::

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
        return self._crud_list(request, models.Instance, self.list_instances)

    @stats.incr_stat('instances.fetch')
    def fetch_instance(self, request, instance_id):
        """Retrieve an instance. Example::

            {
                "id": "e7269c27-abd8-49f1-ba8a-ac063f61bd65",
                "name": "Test Instance B",
                "flavor_id": "d5942a92-ac78-49f6-95c8-d837cfd1f8d2",
                "chassis_id": "5a17df7d-6389-44c3-a01b-7ec5f9e3e33f",
                "state": "ACTIVE"
            }

        Returns 200 with the requested Instance upon success.
        """
        query = models.Instance.objects.filter(id=instance_id)
        return self._crud_fetch(request, models.Instance, query)

    @stats.incr_stat('instances.request_delete')
    def delete_instance(self, request, instance_id):
        """Delete an instance.

        Returns 204 on success.
        """
        try:
            instance = models.Instance.objects.get(id=instance_id)
        except models.Instance.DoesNotExist:
            raise errors.RequestedObjectNotFoundError(models.Instance,
                                                      instance_id)

        if instance.state in (models.InstanceState.DELETING,
                              models.InstanceState.DELETED):
            raise errors.ObjectAlreadyDeletedError(models.Instance,
                                                   instance_id)

        instance.state = models.InstanceState.DELETING
        instance.save()

        self.job_client.submit_job('instances.delete',
                                   instance_id=instance.id)

        return responses.DeletedResponse()


class CarbidePublicAPIServer(component.APIServer):

    """Server for the carbide overlord API."""

    def __init__(self, config, job_client=None):
        super(CarbidePublicAPIServer, self).__init__()
        self.config = config
        self.add_component('/v1',
                           CarbidePublicAPI(self.config, job_client=job_client))
