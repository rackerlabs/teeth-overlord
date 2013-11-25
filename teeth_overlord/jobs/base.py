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
from uuid import uuid4
import time

from structlog import get_logger

from teeth_overlord.models import (
    JobRequest,
    JobRequestState
)
from teeth_overlord.agent_client import AgentClient
from teeth_overlord.service import SynchronousTeethService
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


class JobExecutor(SynchronousTeethService):
    """
    A service which executes job requests from a queue.
    """

    def __init__(self, config):
        self.config = config
        self.log = get_logger()
        self.agent_client = AgentClient(config)
        self.image_provider = get_image_provider(config.IMAGE_PROVIDER, config.IMAGE_PROVIDER_CONFIG)
        self.scheduler = TeethInstanceScheduler()
        self.queue = MarconiClient(base_url=config.MARCONI_URL)
        self._job_type_cache = {}

    def _get_job_class(self, job_type):
        if job_type not in self._job_type_cache:
            self._job_type_cache[job_type] = next(cls for cls in Job.__subclasses__()
                                                  if cls.job_type == job_type)

        return self._job_type_cache[job_type]

    def _process_next_message(self):
        try:
            message = self.queue.claim_message(JOB_QUEUE_NAME, CLAIM_TTL, CLAIM_GRACE)
        except Exception as e:
            # TODO: some sort of backoff if queueing system is down
            self.log.error('error claiming message', exception=e)
            message = None

        # TODO: Process messages in a thread so we can process more messages
        #       concurrently without multiple pollers.
        if not message:
            if not self.stopping:
                time.sleep(POLLING_INTERVAL)
            return

        try:
            job_request = JobRequest.objects.get(id=message.body['job_request_id'])
        except JobRequest.DoesNotExist:
            self.log.info('removing message corresponding to non-existent JobRequest',
                          message_href=message.href,
                          job_request_id=message.body['job_request_id'])
            self.queue.delete_message(message)
            return

        cls = self._get_job_class(job_request.job_type)
        job = cls(self, job_request, message)
        job.execute()

    def run(self):
        """
        Start processing jobs.
        """
        super(JobExecutor, self).run()
        while not self.stopping:
            self._process_next_message()


class JobClient(object):
    """
    A client for submitting job requests.
    """
    def __init__(self, config):
        self.config = config
        self.queue = MarconiClient(base_url=config.MARCONI_URL)

    def submit_job(self, cls, **params):
        """
        Submit a job request. Specify the type of job desired, as well
        as the pareters to the request. Parameters must be a dict
        mapping strings to strings.
        """
        job_request = JobRequest(job_type=cls.job_type, params=params)
        job_request.save()
        body = {'job_request_id': str(job_request.id)}
        return self.queue.push_message(JOB_QUEUE_NAME, body, JOB_TTL)


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
        try:
            self.request.save()
        except Exception as e:
            self.log.error('error saving JobRequest, ignoring', exception=e)

    def _update_claim(self, ttl=CLAIM_TTL):
        try:
            self.executor.queue.update_claim(self.message, ttl)
        except Exception as e:
            self.log.error('error updating claim on message, ignoring', exception=e)

    def _delete_message(self):
        try:
            self.executor.queue.delete_message(self.message)
        except Exception as e:
            self.log.error('error deleting message, ignoring', exception=e)

    def _reset_request(self):
        self.request.reset()
        if self.request.failed_attempts >= self.max_retries:
            self.log.info('job request exceeded retry limit', max_retries=self.max_retries)
            self.request.fail()
            self._save_request()
            self._delete_message()
        else:
            self._save_request()
            self._update_claim(ttl=INITIAL_RETRY_DELAY)

    def execute(self):
        """
        Called to execute a job. Marks the request `RUNNING` in the
        database, and periodically updates it until the task either
        completes or fails.
        """
        if self.request.state in (JobRequestState.FAILED, JobRequestState.COMPLETED):
            self.log.info('job request no longer valid, not executing', state=self.request.state)
            self._delete_message()
            return

        if self.request.state == JobRequestState.RUNNING:
            self.log.info('job request was found in RUNNING state, assuming it failed')
            self._reset_request()
            return

        self.log.info('executing job request')
        self.request.start()
        self._save_request()

        try:
            self._execute()
        except Exception as e:
            self.log.error('error executing job', exception=e)
            self._reset_request()
        else:
            self.log.info('successfully executed job request')
            self.request.complete()
            self._save_request()
            self._delete_message()
