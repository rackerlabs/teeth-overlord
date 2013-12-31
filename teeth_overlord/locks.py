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

        self._thread = threading.Thread(target=self._keep_locks_open)
        self._event = threading.Event()
        self._locks = {}

    def _keep_locks_open(self):
        while True:
            now = time.time()
            interval = 60  # poll at least once per minute
            for lock in self._locks.itervalues():
                current_ttl = lock.expires_at - now
                if (current_ttl <= lock.two_thirds_ttl):
                    # need to renew NOW
                    lock.renew(lock.ttl)
                    lock.expires_at = now + lock.ttl
                time_to_renewal = current_ttl - lock.two_thirds_ttl
                interval = min(interval, time_to_renewal)
            self._event.clear()
            self._event.wait(interval)

    def acquire(self, key, ttl=1, value=None):
        lock = self.client.get_lock(key, ttl=ttl, value=value)
        lock.acquire()
        now = time.time()
        lock.expires_at = now + ttl
        lock.two_thirds_ttl = 2.0 * ttl / 3.0
        self._locks[key] = lock
        self._event.set()

    def release(self, key):
        # TODO(jimrollenhagen) wrap in try/except KeyError?
        self._locks[key].release()
        del self._locks[key]
