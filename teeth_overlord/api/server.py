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

import json
from uuid import UUID

from structlog import get_logger
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import BaseRequest, BaseResponse
from werkzeug.exceptions import HTTPException
from werkzeug.http import parse_options_header

from teeth_overlord import models, jobs, errors
from teeth_overlord.images.base import get_image_provider
from teeth_overlord.encoding import TeethJSONEncoder


def _validate_relation(instance, field_name, cls):
    id = getattr(instance, field_name)

    try:
        return cls.get(id=id)
    except cls.DoesNotExist:
        msg = 'Invalid {field_name}, no such {type_name}.'.format(field_name=field_name,
                                                                  type_name=cls.__name__)
        raise errors.InvalidContentError(msg)


class TeethAPI(object):
    """
    The primary Teeth Overlord API.
    """
    def __init__(self, config):
        self.config = config
        self.log = get_logger()
        self.encoder = TeethJSONEncoder('public', indent=4)
        self.job_client = jobs.JobClient(config)
        self.image_provider = get_image_provider(config.IMAGE_PROVIDER, config.IMAGE_PROVIDER_CONFIG)
        self.url_map = Map()
        self.add_routes()

    def add_routes(self):
        """
        Called during initialization. Override to map relative routes to methods.
        """
        # ChassisModel Handlers
        self.route('GET', '/v1.0/chassis_models', self.list_chassis_models)
        self.route('POST', '/v1.0/chassis_models', self.create_chassis_model)

        # Flavor Handlers
        self.route('GET', '/v1.0/flavors', self.list_flavors)
        self.route('POST', '/v1.0/flavors', self.create_flavor)

        # FlavorProvider Handlers
        self.route('GET', '/v1.0/flavor_providers', self.list_flavor_providers)
        self.route('POST', '/v1.0/flavor_providers', self.create_flavor_provider)

        # Chassis Handlers
        self.route('GET', '/v1.0/chassis', self.list_chassis)
        self.route('POST', '/v1.0/chassis', self.create_instance)

        # Instance Handlers
        self.route('GET', '/v1.0/instances', self.list_instances)
        self.route('POST', '/v1.0/instances', self.create_instance)
        self.route('GET', '/v1.0/instances/<string:instance_id>', self.fetch_instance)

    def route(self, method, pattern, fn):
        """
        Route a relative path to a method.
        """
        self.url_map.add(Rule(pattern, methods=[method], endpoint=fn))

    def dispatch_request(self, request):
        """
        Given a Werkzeug request, generate a Response.
        """
        url_adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = url_adapter.match()
            return endpoint(request, **values)
        except errors.TeethError as e:
            self.log.error('error handling request', exception=e)
            return self.return_error(request, e)
        except HTTPException as e:
            return e
        except Exception as e:
            self.log.error('error handling request', exception=e)
            return self.return_error(request, errors.TeethError())

    def __call__(self, environ, start_response):
        request = BaseRequest(environ)
        return self.dispatch_request(request)(environ, start_response)

    def get_absolute_url(self, request, path):
        """
        Given a request and an absolute path, attempt to construct an
        absolute URL by examining the `Host` and `X-Forwarded-Proto`
        headers.
        """
        host = request.headers.get('host')
        proto = request.headers.get('x-forwarded-proto', default='http')
        return "{proto}://{host}{path}".format(proto=proto, host=host, path=path)

    def return_ok(self, request, result):
        """
        Return 200 and serialize the correspondig result.
        """
        body = self.encoder.encode(result)
        return BaseResponse(body, status=200, content_type='application/json')

    def return_created(self, request, path):
        """
        Return 201 and a Location generated from `path`.
        """
        response = BaseResponse(status=201, content_type='application/json')
        response.headers.set('Location', self.get_absolute_url(request, path))
        return response

    def return_error(self, request, e):
        """
        Transform a TeethError into the apprpriate response and return it.
        """
        body = self.encoder.encode(e)
        return BaseResponse(body, status=e.status_code, content_type='application/json')

    def parse_content(self, request):
        """
        Extract the content from the passed request, and attempt to
        parse it according to the specified `Content-Type`.

        Note: currently only `application/json` is supported.
        """
        content_type_header = request.headers.get('content-type', default='application/json')
        content_type = parse_options_header(content_type_header)[0]

        if content_type == 'application/json':
            try:
                return json.loads(request.get_data())
            except Exception as e:
                raise errors.InvalidContentError(e.message)
        else:
            raise errors.UnsupportedContentTypeError(content_type)

    def _crud_list(self, request, cls):
        return self.return_ok(request, list(cls.objects.all()))

    def _crud_fetch(self, request, cls, id):
        try:
            return self.return_ok(request, cls.get(id=UUID(id)))
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
        return self.return_created(request, '/v1.0/chassis_model/' + str(chassis_model.id))

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
