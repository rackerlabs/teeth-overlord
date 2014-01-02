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

import contextlib
import threading
import time

import etcd


class EtcdLockManager(object):

    """Manager for etcd-based locks."""

    def __init__(self, config, client=None):
        if client is not None:
            self.client = client
        else:
            self.client = etcd.Client(config.ETCD_HOST, config.ETCD_PORT)

        self._event = threading.Event()
        self._lock = threading.Lock()
        self._locks = {}
        self.stopping = False
        self._thread = threading.Thread(target=self._keep_locks_open)
        self._thread.start()

    def stop(self):
        self.stopping = True
        with self._lock:
            self._event.set()
            self._thread.join()

    def _keep_locks_open(self):
        while not self.stopping:
            now = time.time()
            next_interval = self._check_locks(now)
            self._event.wait(next_interval)

    def _check_locks(self, now):
        interval = 60  # check at least once per minute
        locks = []
        with self._lock:
            locks = self._locks.values()
            self._event.clear()
        for lock in locks:
            time_to_renew = self._check_and_renew(lock, now)
            interval = min(interval, time_to_renew)
        return interval

    def _check_and_renew(self, lock, now):
        if self._should_renew(lock, now):
            # need to renew NOW
            # TODO(jimrollenhagen) add a try/except EtcdException here
            lock.renew(lock.ttl)
            lock.expires_at = now + lock.ttl
        current_ttl = lock.expires_at - now
        time_to_renewal = current_ttl - lock.two_thirds_ttl
        return time_to_renewal

    def _should_renew(self, lock, now):
        current_ttl = lock.expires_at - now
        return current_ttl <= lock.two_thirds_ttl

    @contextlib.contextmanager
    def acquire(self, key, **kwargs):
        self._acquire(key, **kwargs)
        yield
        self._release(key)

    def _acquire(self, key, ttl=1, value=None):
        lock = self.client.get_lock(key, ttl=ttl, value=value)
        lock.acquire()
        now = time.time()
        lock.expires_at = now + ttl
        lock.two_thirds_ttl = 2.0 * ttl / 3.0
        with self._lock:
            self._locks[key] = lock
            self._event.set()

    def _release(self, key):
        # TODO(jimrollenhagen) wrap in try/except KeyError?
        self._locks[key].release()
        del self._locks[key]
