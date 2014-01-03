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
        self._thread.daemon = True
        self._thread.start()

    def __del__(self):
        self.stopping = True
        with self._lock:
            self._event.set()
        self._thread.join()

    def _keep_locks_open(self):
        while not self.stopping:
            next_update = self._check_locks()
            now = time.time()
            next_interval = next_update - now
            # if next interval is negative, loop immediately
            if next_interval > 0:
                self._event.wait(next_interval)

    def _check_locks(self):
        next_update = time.time() + 60  # check at least once per minute
        locks = []
        with self._lock:
            locks = self._locks.values()
            self._event.clear()
        for lock in locks:
            time_to_renew = self._check_and_renew(lock)
            next_update = min(next_update, time_to_renew)
        return next_update

    def _check_and_renew(self, lock):
        if self._should_renew(lock):
            try:
                lock.renew(lock.ttl)
            except etcd.EtcdException:
                # lock was released or expired, clean it up
                self._release(lock.key)
            lock.expires_at = time.time() + lock.ttl
        next_update = lock.expires_at - lock.two_thirds_ttl
        return next_update

    def _should_renew(self, lock):
        now = time.time()
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
        with self._lock:
            lock = self._locks[key]
            del self._locks[key]
        try:
            lock.release()
        except etcd.EtcdException:
            # lock was already released or expired
            pass
