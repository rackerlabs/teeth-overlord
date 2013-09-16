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
from twisted.python import log

from teeth.overlord import models, jobs, errors


class TeethAPI(object):
    app = Klein()
    encoder = models.ModelEncoder('public', indent=4)

    def __init__(self, config):
        self.config = config

    def get_absolute_url(self, request, path):
        host = request.getHeader('host')
        proto = request.getHeader('x-forwarded-proto') or 'http'
        return "{proto}://{host}{path}".format(proto=proto, host=host, path=path)

    def return_error(self, failure, request):
        error = failure.value
        log.err(failure)
        if isinstance(error, errors.TeethError):
            request.setResponseCode(error.status_code)
            request.setHeader('Content-Type', 'application/json')
            return self.encoder.encode(error)
        else:
            request.setResponseCode(500)
            request.setHeader('Content-Type', 'application/json')
            return self.encoder.encode(errors.TeethError())

    @app.route('/v1.0/chassis', methods=['POST'])
    def create_chassis(self, request):
        def _saved(chassis):
            request.setHeader('Location', self.get_absolute_url(request, '/v1.0/chassis/' + str(chassis.id)))
            request.setResponseCode(201)

        chassis = models.Chassis(primary_mac_address='foo')
        return threads.deferToThread(chassis.save).addCallback(_saved)

    @app.route('/v1.0/chassis', methods=['GET'])
    def list_chassis(self, request):
        def _retrieved(chassis):
            request.setHeader('Content-Type', 'application/json')
            return self.encoder.encode(chassis)

        chassis_query = models.Chassis.objects.all()
        return threads.deferToThread(list, chassis_query).addCallback(_retrieved)

    @app.route('/v1.0/instances', methods=['POST'])
    def create_instance(self, request):
        instance = models.Instance()
        job = jobs.CreateInstanceJob(instance)

        def _created(instance):
            request.setHeader('Location', self.get_absolute_url(request, '/v1.0/instances/' + str(instance.id)))
            request.setResponseCode(201)

        return job.execute().addCallback(_created).addErrback(self.return_error, request)

    @app.route('/v1.0/instances', methods=['GET'])
    def list_instances(self, request):
        def _retrieved(instances):
            request.setHeader('Content-Type', 'application/json')
            return self.encoder.encode(instances)

        return threads.deferToThread(list, models.Instance.objects.all()).addCallback(_retrieved)

    def run(self):
        self.app.run(self.config.API_HOST, self.config.API_PORT)
