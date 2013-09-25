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
from twisted.internet import threads

from teeth_overlord import models, jobs, rest


class TeethAPI(rest.RESTServer):
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
        def _saved(chassis_model):
            request.setHeader('Location', self.get_absolute_url(request, '/v1.0/chassis_model/' + str(chassis_model.id)))
            request.setResponseCode(201)

        try:
            chassis_model = models.ChassisModel.deserialize(self.parse_content(request))
            return threads.deferToThread(chassis_model.save).addCallback(_saved)
        except Exception as e:
            return self.return_error(e, request)

    @app.route('/v1.0/chassis_models', methods=['GET'])
    def list_chassis_model(self, request):
        return self._crud_list(request, models.ChassisModel)

    @app.route('/v1.0/chassis', methods=['POST'])
    def create_chassis(self, request):
        def _saved(chassis):
            request.setHeader('Location', self.get_absolute_url(request, '/v1.0/chassis/' + str(chassis.id)))
            request.setResponseCode(201)

        try:
            chassis = models.Chassis.deserialize(self.parse_content(request))
            return threads.deferToThread(chassis.save).addCallback(_saved)
        except Exception as e:
            return self.return_error(e, request)

    @app.route('/v1.0/chassis', methods=['GET'])
    def list_chassis(self, request):
        return self._crud_list(request, models.Chassis)

    @app.route('/v1.0/instances', methods=['POST'])
    def create_instance(self, request):
        instance = models.Instance()

        def _execute_job(result):
            return self.job_client.submit_job(jobs.CreateInstance, instance_id=str(instance.id))

        def _respond(result):
            request.setHeader('Location', self.get_absolute_url(request, '/v1.0/instances/' + str(instance.id)))
            request.setResponseCode(201)
            return

        return threads.deferToThread(instance.save) \
                      .addCallback(_execute_job) \
                      .addCallback(_respond) \
                      .addErrback(self.return_error, request)

    @app.route('/v1.0/instances', methods=['GET'])
    def list_instances(self, request):
        return self._crud_list(request, models.Instance)
