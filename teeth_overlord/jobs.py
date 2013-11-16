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
from txetcd.client import EtcdClient
from txetcd.locking import EtcdLockManager

from teeth_overlord.models import (
    ChassisState,
    Instance,
    InstanceState,
    JobRequest,
    JobRequestState
)
from teeth_overlord.agent.rpc import EndpointRPCClient
from teeth_overlord.service import TeethService
from teeth_overlord.scheduler import TeethInstanceScheduler
from teeth_overlord.images.base import get_image_provider
from teeth_overlord.marconi import MarconiClient


JOB_QUEUE_NAME = 'teeth_jobs'

# Use a very high TTL on Marconi messages - we never really want them to
# expire. If we give up on a message, we'll expire it ourselves.
JOB_TTL = 60 * 60 * 24 * 14

# Claim messages for 2 minutes. This tries to establish a balance between how
# long a message can become "stuck" if we die while processing it, while not
# requiring overly frequent updates. In particular, if updates are required
# frequently (say, every few seconds), it is easy to miss an update and end up
# losing our claim to someone else.
CLAIM_TTL = 60

# When a temporal job failure occurs, we back off exponentially.
INITIAL_RETRY_DELAY = 60
MAX_RETRY_DELAY = 3600
BACKOFF_FACTOR = 1.5
JITTER = .2

# Failing to process a job should return it to the queue with as long a grace
# period as we can manage.
CLAIM_GRACE = 60 * 60 * 12

# Poll frequently. Help keep build times low.
POLLING_INTERVAL = 0.1


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
        self.lock_manager = EtcdLockManager(self.etcd_client, '/teeth/locks')
        self.image_provider = get_image_provider(config.IMAGE_PROVIDER, config.IMAGE_PROVIDER_CONFIG)
        self.scheduler = TeethInstanceScheduler(self.lock_manager)
        self.queue = MarconiClient(base_url=config.MARCONI_URL)
        self._looper = task.LoopingCall(self._take_next_message)
        self._pending_calls = set()
        self._job_type_cache = {}

    def _get_job_class(self, job_type):
        if job_type not in self._job_type_cache:
            self._job_type_cache[job_type] = next(cls for cls in Job.__subclasses__()
                                                  if cls.job_type == job_type)

        return self._job_type_cache[job_type]

    def _load_job_request(self, message):
        def _load_error(failure):
            if failure.check(JobRequest.DoesNotExist):
                self.log.msg('removing message corresponding to non-existent JobRequest',
                             message_href=message.href,
                             job_request_id=message.body['job_request_id'])
                return self.queue.delete_message(message).addCallback(lambda result: failure)
            else:
                return failure

        d = threads.deferToThread(JobRequest.objects.get, id=UUID(message.body['job_request_id']))
        return d.addCallbacks(lambda job_request: (job_request, message), _load_error)

    def _execute_job_request(self, (job_request, message)):
        cls = self._get_job_class(job_request.job_type)
        job = cls(self, job_request, message)
        d = job.execute()
        self._pending_calls.add(d)
        d.addBoth(lambda result: self._pending_calls.remove(d))

    def _take_next_message(self):
        d = self.queue.claim_message(JOB_QUEUE_NAME, CLAIM_TTL, CLAIM_GRACE,
                                     polling_interval=POLLING_INTERVAL)
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
        self.queue = MarconiClient(base_url=config.MARCONI_URL)

    def _notify_workers(self, job_request):
        body = {'job_request_id': str(job_request.id)}
        return self.queue.push_message(JOB_QUEUE_NAME, body, JOB_TTL)

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

    def __init__(self, executor, request, message):
        self.executor = executor
        self.params = request.params
        self.request = request
        self.message = message
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

    def _update_claim(self, ttl=CLAIM_TTL):
        return self.executor.queue.update_claim(self.message, ttl).addErrback(self.log.err)

    def _release_claim(self):
        return self.executor.queue.release_claim(self.message).addErrback(self.log.err)

    def _delete_message(self):
        return self.executor.queue.delete_message(self.message).addErrback(self.log.err)

    def _on_success(self, result):
        self.log.msg('successfully executed job request')
        self.request.complete()
        d = self._save_request()
        d.addBoth(lambda result: self._delete_message())

    def _on_error(self, failure):
        self.log.err(failure)
        return self._reset_request()

    def _reset_request(self):
        self.request.reset()
        if self.request.failed_attempts >= self.max_retries:
            self.log.msg('job request exceeded retry limit', max_retries=self.max_retries)
            self.request.fail()
            d = self._save_request()
            d.addBoth(lambda result: self._delete_message())
            return d
        else:
            d = self._save_request()
            d.addBoth(lambda result: self._update_claim(ttl=INITIAL_RETRY_DELAY))
            return d

    def execute(self):
        """
        Called to execute a job. Marks the request `RUNNING` in the
        database, and periodically updates it until the task either
        completes or fails.
        """
        if self.request.state in (JobRequestState.FAILED, JobRequestState.COMPLETED):
            self.log.msg('job request no longer valid, not executing', state=self.request.state)
            return self._delete_message()

        if self.request.state == JobRequestState.RUNNING:
            self.log.msg('job request was found in RUNNING state, assuming it failed')
            return self._reset_request()

        self.log.msg('executing job request')
        self.request.start()
        self._save_request().addBoth(lambda result: self._update_claim())
        return self._execute().addCallback(self._on_success).addErrback(self._on_error)


class CreateInstance(Job):
    """
    Job which creates an instance. In order to return a 201 response to
    the user, we actually create an Instance in the database in the
    `BUIlD` state prior to executing this job, but it is up to the job
    to select and provision an appropriate chassis based on the instance
    parameters.
    """
    job_type = 'create_instance'
    max_retries = 10

    def get_instance(self):
        """
        Load the instance from the database.
        """
        instance_id = self.request.params['instance_id']
        return threads.deferToThread(Instance.objects.get, id=UUID(instance_id))

    def reserve_chassis(self, instance):
        """
        Reserve a chassis for use by the instance.
        """
        d = self.executor.scheduler.reserve_chassis(instance)
        d.addCallback(lambda chassis: (instance, chassis))
        return d

    def retrieve_image_info(self, (instance, chassis)):
        """
        Retrieve info about the requested image.
        """
        d = self.executor.image_provider.get_image_info(instance.image_id)
        d.addCallback(lambda image_info: (instance, chassis, image_info))
        return d

    def get_agent_connection(self, (instance, chassis, image_info)):
        """
        Load the agent connection for the selected chassis.
        """
        client = self.executor.endpoint_rpc_client
        d = client.get_agent_connection(chassis)
        d.addCallback(lambda connection: (instance, chassis, image_info, connection))
        return d

    def prepare_image(self, (instance, chassis, image_info, connection)):
        """
        Send a command to the agent to prepare the selected image.
        """
        client = self.executor.endpoint_rpc_client
        d = client.prepare_image(connection, image_info)
        d.addCallback(lambda result: (instance, chassis, image_info, connection))
        return d

    def run_image(self, (instance, chassis, image_info, connection)):
        """
        Send a command to the agent to run the selected image.
        """
        client = self.executor.endpoint_rpc_client
        d = client.run_image(connection, image_info)
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
        d.addCallback(self.reserve_chassis)
        d.addCallback(self.retrieve_image_info)
        d.addCallback(self.get_agent_connection)
        d.addCallback(self.prepare_image)
        d.addCallback(self.run_image)
        d.addCallback(self.mark_active)
        return d
