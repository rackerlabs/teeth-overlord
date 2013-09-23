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

from abc import ABCMeta, abstractproperty, abstractmethod
from uuid import UUID

from klein import Klein
from twisted.internet import threads
from cqlengine import BatchQuery

from teeth_overlord.models import Chassis, ChassisState, Instance, InstanceState, JobRequest
from teeth_overlord import errors
from teeth_overlord.agent.rpc import EndpointRPCClient
from teeth_overlord.rest import RESTServer


class JobExecutor(RESTServer):
    app = Klein()

    def __init__(self, config):
        RESTServer.__init__(self, config, config.JOBSERVER_HOST, config.JOBSERVER_PORT)
        self.endpoint_rpc_client = EndpointRPCClient(config)
        self._job_type_cache = {}

    def _get_job_class(self, job_type):
        if job_type not in self._job_type_cache:
            self._job_type_cache[job_type] = next(cls for cls in Job.__subclasses__() if cls.job_type == job_type)

        return self._job_type_cache[job_type]

    @app.route('/v1.0/job_requests/<string:request_id>/execute', methods=['POST'])
    def execute_job_request(self, request, request_id):
        def _with_request(job_request):
            cls = self._get_job_class(job_request.job_type)
            job = cls(self, job_request)
            job.execute()
            return

        request_id = UUID(request_id)
        return threads.deferToThread(JobRequest.objects.get, id=request_id).addCallback(_with_request)


class JobClient(object):
    def __init__(self, config):
        self.config = config
        self.executor = JobExecutor(config)

    def submit_job(self, cls, **params):
        job_request = JobRequest(job_type=cls.job_type, params=params)

        def _on_save(result):
            return self.executor.execute_job_request(None, str(job_request.id))

        return threads.deferToThread(job_request.save).addCallback(_on_save)


class Job(object):
    __metaclass__ = ABCMeta

    def __init__(self, executor, request):
        self.executor = executor
        self.params = request.params
        self.request = request

    @abstractproperty
    def job_type(self):
        raise NotImplementedError()

    @abstractmethod
    def execute(self):
        raise NotImplementedError()


class CreateInstance(Job):
    job_type = 'create_instance'

    def get_instance(self):
        instance_id = self.request.params['instance_id']
        return threads.deferToThread(Instance.objects.get, id=UUID(instance_id))

    def find_chassis(self, instance):
        ready_query = Chassis.objects.filter(state=ChassisState.READY)
        return threads.deferToThread(ready_query.first).addCallback(lambda chassis: (instance, chassis))

    def reserve_chassis(self, (instance, chassis)):
        if not chassis:
            raise errors.InsufficientCapacityError()

        batch = BatchQuery()
        instance.chassis_id = chassis.id
        instance.state = InstanceState.BUILD
        instance.batch(batch).save()
        chassis.state = ChassisState.BUILD
        chassis.batch(batch).save()
        return threads.deferToThread(batch.execute).addCallback(lambda result: (instance, chassis))

    def get_agent_connection(self, (instance, chassis)):
        client = self.executor.endpoint_rpc_client
        return client.get_agent_connection(chassis).addCallback(lambda connection: (instance, chassis, connection))

    def prepare_image(self, (instance, chassis, connection)):
        print connection
        client = self.executor.endpoint_rpc_client
        return client.prepare_image(connection, 'image-123').addCallback(lambda result: (instance, chassis))

    def mark_active(self, (instance, chassis)):
        batch = BatchQuery()
        instance.chassis_id = chassis.id
        instance.state = InstanceState.ACTIVE
        instance.batch(batch).save()
        chassis.state = ChassisState.ACTIVE
        chassis.batch(batch).save()
        return threads.deferToThread(batch.execute).addCallback(lambda result: None)

    def execute(self):
        return self.get_instance() \
                   .addCallback(self.find_chassis) \
                   .addCallback(self.reserve_chassis) \
                   .addCallback(self.get_agent_connection) \
                   .addCallback(self.prepare_image) \
                   .addCallback(self.mark_active) \
                   .addCallback(self.done)
