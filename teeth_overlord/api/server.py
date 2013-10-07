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
from twisted.python import failure

from teeth_overlord import models, jobs, rest


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

    @app.route('/v1.0/chassis_models', methods=['POST'])
    def create_chassis_model(self, request):
        """
        Create a ChassisModel.
        """
        def _saved(chassis_model):
            return self.return_created(request, '/v1.0/chassis_model/' + str(chassis_model.id))

        try:
            chassis_model = models.ChassisModel.deserialize(self.parse_content(request))
            return threads.deferToThread(chassis_model.save).addCallback(_saved)
        except Exception as e:
            return self.return_error(e, request)

    @app.route('/v1.0/chassis_models', methods=['GET'])
    def list_chassis_model(self, request):
        """
        List ChassisModels.
        """
        return self._crud_list(request, models.ChassisModel)

    @app.route('/v1.0/flavors', methods=['POST'])
    def create_flavor(self, request):
        """
        Create a Flavor.
        """
        def _saved(flavor):
            return self.return_created(request, '/v1.0/flavor/' + str(flavor.id))

        try:
            flavor = models.Flavor.deserialize(self.parse_content(request))
            return threads.deferToThread(flavor.save).addCallback(_saved)
        except Exception as e:
            return self.return_error(e, request)

    @app.route('/v1.0/flavors', methods=['GET'])
    def list_flavor(self, request):
        """
        List Flavors.
        """
        return self._crud_list(request, models.Flavor)

    @app.route('/v1.0/flavor_providers', methods=['POST'])
    def create_flavor_provider(self, request):
        """
        Create a FlavorProvider, which maps a Flavor to a ChassisModel.
        """
        def _saved(flavor_provider):
            return self.return_created(request, '/v1.0/flavor_provider/' + str(flavor_provider.id))

        def _validated(results):
            return threads.deferToThread(flavor_provider.save).addCallback(_saved)

        try:
            flavor_provider = models.FlavorProvider.deserialize(self.parse_content(request))
            d = defer.gatherResults([
                threads.deferToThread(models.ChassisModel.get, id=flavor_provider.chassis_model_id),
                threads.deferToThread(models.Flavor.get, id=flavor_provider.flavor_id),
            ])
            d.addCallback(_validated)
            d.addErrback(self.return_error, request)
            return d
        except Exception as e:
            return self.return_error(e, request)

    @app.route('/v1.0/flavor_providers', methods=['GET'])
    def list_flavor_provider(self, request):
        """
        List FlavorProviders.
        """
        return self._crud_list(request, models.FlavorProvider)

    @app.route('/v1.0/chassis', methods=['POST'])
    def create_chassis(self, request):
        """
        Create a Chassis.

        TODO: actually bootstrap the chassis to a `READY` state, change teh passwords, etc.
        """
        def _saved(chassis):
            return self.return_created(request, '/v1.0/chassis/' + str(chassis.id))

        def _with_chassis_model(chassis_model, chassis):
            chassis.ipmi_username = chassis_model.ipmi_default_username
            chassis.ipmi_password = chassis_model.ipmi_default_password
            return threads.deferToThread(chassis.save).addCallback(_saved)

        try:
            chassis = models.Chassis.deserialize(self.parse_content(request))
            d = threads.deferToThread(models.ChassisModel.objects.get, id=chassis.chassis_model_id)
            d.addCallback(_with_chassis_model, chassis)
            d.addErrback(self.return_error, request)
            return d
        except Exception as e:
            return self.return_error(failure.Failure(e), request)

    @app.route('/v1.0/chassis', methods=['GET'])
    def list_chassis(self, request):
        """
        List Chassis.
        """
        return self._crud_list(request, models.Chassis)

    @app.route('/v1.0/instances', methods=['POST'])
    def create_instance(self, request):
        """
        Create an Instance.
        """

        def _execute_job(result):
            return self.job_client.submit_job(jobs.CreateInstance, instance_id=str(instance.id))

        def _respond(result):
            return self.return_created(request, '/v1.0/instances/' + str(instance.id))

        try:
            instances = models.Instance.deserialize(self.parse_content(request))
            d = threads.deferToThread(instance.save)
            d.addCallback(_execute_job)
            d.addCallback(_respond)
            d.addErrback(self.return_error, request)
            return d

        except Exception as e:
            return self.return_error(e, request)

    @app.route('/v1.0/instances', methods=['GET'])
    def list_instances(self, request):
        """
        List Instances.
        """
        return self._crud_list(request, models.Instance)
