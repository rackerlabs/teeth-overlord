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

import abc
import signal
import threading
import uuid

from stevedore import driver
import structlog

from teeth_overlord import agent_client
from teeth_overlord.images import base as images_base
from teeth_overlord import locks
from teeth_overlord import marconi
from teeth_overlord import models
from teeth_overlord.networks import base as networks_base
from teeth_overlord.oob import base as oob_base
from teeth_overlord import scheduler
from teeth_overlord import service
from teeth_overlord import stats


JOB_QUEUE_NAME = 'teeth_jobs'

JOB_DRIVER_NAMESPACE = 'teeth_overlord.jobs'

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


class JobExecutor(service.SynchronousTeethService):

    """A service which executes job requests from a queue."""

    def __init__(self, config):
        super(JobExecutor, self).__init__(config)
        self.config = config
        self.log = structlog.get_logger()
        self.agent_client = agent_client.get_agent_client(config)
        self.job_client = JobClient(config)
        self.image_provider = images_base.get_image_provider(config)
        self.oob_provider = oob_base.get_oob_provider(config)
        self.network_provider = networks_base.get_network_provider(config)
        self.scheduler = scheduler.TeethInstanceScheduler()
        self.claim_lock = threading.Lock()
        self.queue = marconi.MarconiClient(base_url=config.MARCONI_URL)
        self.stats_client = stats.get_stats_client(config, 'jobs')
        self.concurrent_jobs_gauge = stats.ConcurrencyGauge(self.stats_client,
                                                            'concurrent_jobs')
        self._job_type_cache = {}

    def _get_job_class(self, job_type):
        if job_type not in self._job_type_cache:
            self._job_type_cache[job_type] = driver.DriverManager(
                namespace=JOB_DRIVER_NAMESPACE,
                name=job_type,
            )

        return self._job_type_cache[job_type].driver

    def _process_next_message(self):
        with self.claim_lock:
            # Now that we actually have the lock, bail out early if we're
            # supposed to be stopping
            if self.stopping.isSet():
                return

            try:
                message = self.queue.claim_message(JOB_QUEUE_NAME,
                                                   CLAIM_TTL,
                                                   CLAIM_GRACE)
            except Exception as e:
                # TODO(russellhaering): some sort of backoff if queueing system
                # is down
                self.log.error('error claiming message', exception=e)
                message = None

            if not message:
                # Wait up to POLLING_INTERVAL seconds before releasing the
                # lock, but bail out early if the stopping flag gets set.
                self.stopping.wait(POLLING_INTERVAL)
                return

        job_request_id = message.body['job_request_id']

        try:
            job_request = models.JobRequest.objects.get(id=job_request_id)
        except models.JobRequest.DoesNotExist:
            self.log.info('removing message corresponding to non-existent'
                          ' JobRequest',
                          message_href=message.href,
                          job_request_id=job_request_id)

            self.queue.delete_message(message)
            return

        with self.concurrent_jobs_gauge:
            cls = self._get_job_class(job_request.job_type)
            job = cls(self, job_request, message, self.config)
            job.execute()

    def _process_messages(self):
        while not self.stopping.isSet():
            self._process_next_message()

    def run(self):
        """Start processing jobs."""
        super(JobExecutor, self).run()
        threads = [threading.Thread(target=self._process_messages)
                   for i in xrange(0, self.config.JOB_EXECUTION_THREADS)]

        for thread in threads:
            thread.start()

        signal.pause()

        for thread in threads:
            thread.join()


class JobClient(object):

    """A client for submitting job requests."""

    def __init__(self, config):
        self.config = config
        self.queue = marconi.MarconiClient(base_url=config.MARCONI_URL)

    def submit_job(self, job_type, **params):
        """Submit a job request. Specify the type of job desired, as
        well as the pareters to the request. Parameters must be a dict
        mapping strings to strings.
        """
        job_request = models.JobRequest(job_type=job_type, params=params)
        job_request.save()

        body = {'job_request_id': str(job_request.id)}
        return self.queue.push_message(JOB_QUEUE_NAME, body, JOB_TTL)


class Job(object):

    """Abstract base class for defining jobs. Implementations must
    override `_execute` and be registered as a stevedore plugin
    under the `teeth_overlord.jobs` namespace.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, executor, request, message, config):
        self.executor = executor
        # XXX this is a bit hacky, may want to refactor in the future
        self.stats_client = executor.stats_client
        self.params = request.params
        self.request = request
        self.message = message
        self.config = config
        self.lock_manager = locks.EtcdLockManager(config)
        self.log = structlog.get_logger(request_id=str(self.request.id),
                                        attempt_id=str(uuid.uuid4()),
                                        job_type=request.job_type)

    @abc.abstractmethod
    def _execute(self):
        raise NotImplementedError()

    def _save_request(self):
        try:
            self.request.save()
            self._mark_assets()
        except Exception as e:
            self.log.error('error saving JobRequest, ignoring', exception=e)

    def _update_claim(self, ttl=CLAIM_TTL):
        try:
            self.executor.queue.update_claim(self.message, ttl)
        except Exception as e:
            self.log.error('error updating claim on message, ignoring',
                           exception=e)

    def _delete_message(self):
        try:
            self.executor.queue.delete_message(self.message)
        except Exception as e:
            self.log.error('error deleting message, ignoring', exception=e)

    def _reset_request(self):
        self.request.reset()
        if self.request.failed_attempts >= self.max_retries:
            self.log.info('job request exceeded retry limit',
                          max_retries=self.max_retries)
            self.request.fail()
            self._save_request()
            self._delete_message()
        else:
            self._save_request()
            self._update_claim(ttl=INITIAL_RETRY_DELAY)

    @abc.abstractmethod
    def _mark_assets(self):
        raise NotImplementedError()

    def execute(self):
        """Called to execute a job. Marks the request `RUNNING` in the
        database, and periodically updates it until the task either
        completes or fails.
        """
        if self.request.state in (models.JobRequestState.FAILED,
                                  models.JobRequestState.COMPLETED):
            self.log.info('job request no longer valid, not executing',
                          state=self.request.state)
            self._delete_message()
            return

        if self.request.state == models.JobRequestState.RUNNING:
            self.log.info('job request was found in RUNNING state, assuming'
                          ' it failed')
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
