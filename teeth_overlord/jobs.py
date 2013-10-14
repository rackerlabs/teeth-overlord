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

from teeth_overlord.models import (Chassis, ChassisState, Instance, InstanceState, JobRequest,
                                   JobRequestState, FlavorProvider)
from teeth_overlord import errors
from teeth_overlord.agent.rpc import EndpointRPCClient
from teeth_overlord.service import TeethService

JOB_QUEUE_NAME = 'teeth/jobs'


def parse_etcd_seeds(addresses):
    """
    Split a list of strings in the format "<host>:<port>" into tuples
    of (host, port).
    """
    return [tuple(address.rsplit(':')) for address in addresses]


class JobExecutor(TeethService):
    """
    A service which executes job requests from a queue.
    """
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
            self._job_type_cache[job_type] = next(cls for cls in Job.__subclasses__()
                                                  if cls.job_type == job_type)

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
        """
        Start processing jobs.
        """
        TeethService.startService(self)
        self._looper.start(0)

    def stopService(self):
        """
        Stop processing jobs. Attempt to complete any ongoing jobs
        before firing the returned deferred.
        """
        self._looper.stop()
        return defer.gatherResults(list(self._pending_calls))


class JobClient(object):
    """
    A client for submitting job requests.
    """
    def __init__(self, config):
        self.config = config
        self.log = get_logger()
        self.endpoint_rpc_client = EndpointRPCClient(config)
        self.etcd_client = EtcdClient(seeds=parse_etcd_seeds(config.ETCD_ADDRESSES))
        self._queue = EtcdTaskQueue(self.etcd_client, JOB_QUEUE_NAME)

    def _notify_workers(self, job_request):
        return self._queue.push(str(job_request.id))

    def submit_job(self, cls, **params):
        """
        Submit a job request. Specify the type of job desired, as well
        as the pareters to the request. Parameters must be a dict
        mapping strings to strings.
        """
        job_request = JobRequest(job_type=cls.job_type, params=params)
        return threads.deferToThread(job_request.save).addCallback(self._notify_workers)


class Job(object):
    """
    Abstract base class for defining jobs. Implementations must
    override `job_type` and `_execute`.
    """
    __metaclass__ = ABCMeta

    def __init__(self, executor, request, task):
        self.executor = executor
        self.params = request.params
        self.request = request
        self.task = task
        self.log = get_logger(request_id=str(self.request.id), attempt_id=str(uuid4()))

    @abstractproperty
    def job_type(self):
        """
        An ascii string uniquely identifying the type of the job. Will be used to map serialized
        requests to the appropriate implementation, so you don't want to go changing this.
        """
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
        """
        Called to execute a job. Marks the request `RUNNING` in the
        database, and periodically updates it until the task either
        completes or fails.
        """
        if self.request.state in (JobRequestState.FAILED, JobRequestState.COMPLETED):
            self.log.msg('job request no longer valid, not executing', state=self.request.state)
            return defer.succeed(None)

        self.log.msg('executing job request')
        self.request.start()
        self._save_request()
        return self._execute().addCallback(self._on_success).addErrback(self._on_failure)


class CreateInstance(Job):
    """
    Job which creates an instance. In order to return a 201 response to
    the user, we actually create an Instance in the database in the
    `BUIlD` state prior to executing this job, but it is up to the job
    to select and provision an appropriate chassis based on the instance
    parameters.
    """
    job_type = 'create_instance'

    def get_instance(self):
        """
        Load the instance from the database.
        """
        instance_id = self.request.params['instance_id']
        return threads.deferToThread(Instance.objects.get, id=UUID(instance_id))

    def find_flavor_provider(self, instance):
        """
        Find the join object that will give the information about which chassies are available

        """
        ready_query = FlavorProvider.objects.filter(id=instance.flavor_id).order_by('schedule_priority')

        d = threads.deferToThread(ready_query.first)
        d.addCallback(lambda flavor_provider: (instance, flavor_provider))
        return d

    def find_chassis(self, (instance, flavor_provider)):
        """
        Select an appropriate chassis for the instance to run on.

        TODO: eventually we may want to make scheduling very
              extensible.
        """
        ready_query = Chassis.objects.filter(state=ChassisState.READY)
        ready_query = ready_query.filter(id=flavor_provider.chassis_model_id)

        d = threads.deferToThread(ready_query.first)
        d.addCallback(lambda chassis: (instance, chassis))
        return d

    def reserve_chassis(self, (instance, chassis)):
        """
        Mark the selected chassis as belonging to this instance, and
        put it into a `BUILD` state.

        TODO: locking.
        """
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
        """
        Load the agent connection for the selected chassis.
        """
        client = self.executor.endpoint_rpc_client
        d = client.get_agent_connection(chassis)
        d.addCallback(lambda connection: (instance, chassis, connection))
        return d

    def prepare_image(self, (instance, chassis, connection)):
        """
        Send a command to the agent to prepare the selected image.

        TODO: this exists only to demonstrate agent RPC. We will likely
              need to replace this with one or more 'real' steps
              required to prep a chassis.
        """
        client = self.executor.endpoint_rpc_client
        d = client.prepare_image(connection, 'image-123')
        d.addCallback(lambda result: (instance, chassis))
        return d

    def mark_active(self, (instance, chassis)):
        """
        Mark the chassis and instance as active.
        """
        batch = BatchQuery()
        instance.chassis_id = chassis.id
        instance.state = InstanceState.ACTIVE
        instance.batch(batch).save()
        chassis.state = ChassisState.ACTIVE
        chassis.batch(batch).save()
        return threads.deferToThread(batch.execute).addCallback(lambda result: None)

    def _execute(self):
        d = self.get_instance()
        d.addCallback(self.find_flavor_provider)
        d.addCallback(self.find_chassis)
        d.addCallback(self.reserve_chassis)
        d.addCallback(self.get_agent_connection)
        d.addCallback(self.prepare_image)
        d.addCallback(self.mark_active)
        return d
