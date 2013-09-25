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
from uuid import UUID, uuid4

from twisted.internet import defer, reactor, threads
from cqlengine import BatchQuery
from structlog import get_logger
from txredisapi import lazyConnection, ConnectionError

from teeth_overlord.models import Chassis, ChassisState, Instance, InstanceState, JobRequest
from teeth_overlord import errors
from teeth_overlord.agent.rpc import EndpointRPCClient
from teeth_overlord.service import TeethService

JOB_LIST_NAME = 'teeth.jobs'


class RedisJobListener(object):
    listen_timeout_seconds = 1
    redis_error_retry_delay = 1.0

    def __init__(self, host, port, processor_fn):
        self.host = host
        self.port = port
        self.processor_fn = processor_fn
        self.log = get_logger(host=host, port=port)
        self.redis = None
        self._stop_d = None
        self._stopping = True

    def _process_item(self, response):
        if not response:
            # This is normal, it just means no job became available
            return

        list_name, request_id = response
        self.log.msg('received job request', request_id=request_id)
        return self.processor_fn(request_id)

    # If redis is down, try not to spin too fast. Otherwise, log the error.
    def _log_failure_and_delay(self, failure):
        delay = 0
        if not failure.check([ConnectionError]):
            delay = self.redis_error_retry_delay
        else:
            self.log.err(failure)

        d = defer.Deferred()
        reactor.callLater(delay, d.callback, None)
        return d

    def _next_item(self):
        if self._stopping:
            self.redis.quit().addErrback(self.log.err).addCallback(self._stop_d.callback)

        d = self.redis.blpop([JOB_LIST_NAME], self.listen_timeout_seconds)
        d.addCallback(self._process_item)
        d.addErrback(self._log_failure_and_delay)
        d.addCallback(lambda result: reactor.callLater(0, self._next_item))

    def _loop(self):
        self._stop_d = defer.Deferred()
        self._next_item()

    def start(self):
        self._stopping = False
        self.redis = lazyConnection(self.host, self.port)
        self._loop()

    def stop(self):
        self._stopping = True
        return self._stop_d


class JobExecutor(TeethService):
    def __init__(self, config):
        self.config = config
        self.endpoint_rpc_client = EndpointRPCClient(config)
        self._job_type_cache = {}

    def _get_job_class(self, job_type):
        if job_type not in self._job_type_cache:
            self._job_type_cache[job_type] = next(cls for cls in Job.__subclasses__() if cls.job_type == job_type)

        return self._job_type_cache[job_type]

    def _start_processor(self, address):
        host, port = address.rsplit(':')
        processor = RedisJobListener(host, int(port), self.execute_job_request)
        processor.start()
        return processor

    def execute_job_request(self, request_id):
        def _with_request(job_request):
            cls = self._get_job_class(job_request.job_type)
            job = cls(self, job_request)
            return job.execute()

        return threads.deferToThread(JobRequest.objects.get, id=UUID(request_id)).addCallback(_with_request)

    def startService(self):
        TeethService.startService(self)
        self._processors = [self._start_processor(address) for address in self.config.REDIS_ADDRESSES]

    def stopService(self):
        return defer.DeferredList([processor.stop() for processor in self._processors])


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
        self.log = get_logger(request_id=str(self.request.id), attempt_id=str(uuid4()))

    @abstractproperty
    def job_type(self):
        raise NotImplementedError()

    @abstractmethod
    def _execute(self):
        raise NotImplementedError()

    def _on_success(self, result):
        self.log.msg('successfully executed job request')
        return threads.deferToThread(self.request.delete)

    def _on_failure(self, failure):
        self.log.err(failure)

    def execute(self):
        self.log.msg('executing job request')
        return self._execute().addCallback(self._on_success).addErrback(self._on_failure)


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

    def _execute(self):
        return self.get_instance() \
                   .addCallback(self.find_chassis) \
                   .addCallback(self.reserve_chassis) \
                   .addCallback(self.get_agent_connection) \
                   .addCallback(self.prepare_image) \
                   .addCallback(self.mark_active)
