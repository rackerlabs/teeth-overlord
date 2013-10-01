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

from twisted.internet import defer, task, threads
from cqlengine import BatchQuery
from structlog import get_logger
from txetcd import EtcdClient
from txetcd.queue import EtcdTaskQueue

from teeth_overlord.models import Chassis, ChassisState, Instance, InstanceState, JobRequest, JobRequestState
from teeth_overlord import errors
from teeth_overlord.agent.rpc import EndpointRPCClient
from teeth_overlord.service import TeethService

JOB_QUEUE_NAME = 'teeth/jobs'


def parse_etcd_seeds(addresses):
    return [tuple(address.rsplit(':')) for address in addresses]


class JobExecutor(TeethService):
    def __init__(self, config):
        self.config = config
        self.log = get_logger()
        self.endpoint_rpc_client = EndpointRPCClient(config)
        self.etcd_client = EtcdClient(seeds=parse_etcd_seeds(config.ETCD_ADDRESSES))
        self._queue = EtcdTaskQueue(self.etcd_client, JOB_QUEUE_NAME)
        self._looper = task.LoopingCall(self._take_next_task)
        self._pending_calls = set()
        self._job_type_cache = {}

    def _get_job_class(self, job_type):
        if job_type not in self._job_type_cache:
            self._job_type_cache[job_type] = next(cls for cls in Job.__subclasses__() if cls.job_type == job_type)

        return self._job_type_cache[job_type]

    def _load_job_request(self, task):
        d = threads.deferToThread(JobRequest.objects.get, id=UUID(task.value))
        return d.addCallback(lambda job_request: (job_request, task))

    def _execute_job_request(self, (job_request, task)):
        cls = self._get_job_class(job_request.job_type)
        job = cls(self, job_request, task)
        d = job.execute()
        self._pending_calls.add(d)
        d.addBoth(lambda result: self._pending_calls.remove(d))

    def _take_next_task(self):
        d = self._queue.take()
        d.addCallback(self._load_job_request)
        d.addCallback(self._execute_job_request)
        return d.addErrback(self.log.err)

    def startService(self):
        TeethService.startService(self)
        self._looper.start(0)

    def stopService(self):
        self._looper.stop()
        return defer.gatherResults(list(self._pending_calls))


class JobClient(object):
    def __init__(self, config):
        self.config = config
        self.log = get_logger()
        self.endpoint_rpc_client = EndpointRPCClient(config)
        self.etcd_client = EtcdClient(seeds=parse_etcd_seeds(config.ETCD_ADDRESSES))
        self._queue = EtcdTaskQueue(self.etcd_client, JOB_QUEUE_NAME)

    def _notify_workers(self, job_request):
        return self._queue.push(str(job_request.id))

    def submit_job(self, cls, **params):
        job_request = JobRequest(job_type=cls.job_type, params=params)
        return threads.deferToThread(job_request.save).addCallback(self._notify_workers)


class Job(object):
    __metaclass__ = ABCMeta

    def __init__(self, executor, request, task):
        self.executor = executor
        self.params = request.params
        self.request = request
        self.task = task
        self.log = get_logger(request_id=str(self.request.id), attempt_id=str(uuid4()))

    @abstractproperty
    def job_type(self):
        raise NotImplementedError()

    @abstractmethod
    def _execute(self):
        raise NotImplementedError()

    def _save_request(self):
        return threads.deferToThread(self.request.save).addErrback(self.log.err)

    def _on_success(self, result):
        self.log.msg('successfully executed job request')
        self.request.complete()
        d = self._save_request()
        d.addBoth(lambda result: self.task.complete())

    def _on_failure(self, failure):
        self.log.err(failure)
        self.request.fail()
        d = self._save_request()
        d.addBoth(lambda result: self.task.abort())

    def execute(self):
        if self.request.state in (JobRequestState.FAILED, JobRequestState.COMPLETED):
            self.log.msg('job request no longer valid, not executing', state=self.request.state)
            return defer.succeed(None)

        self.log.msg('executing job request')
        self.request.start()
        self._save_request()
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
