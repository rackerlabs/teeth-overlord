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

import time
import unittest

import etcd
import mock

from carbide_overlord import config
from carbide_overlord import locks


class MockLock(object):
    def __init__(self, key, ttl=None, value=None):
        self.key = key
        self.ttl = ttl
        self.value = value

    def _noop(self, *args, **kwargs):
        pass
    acquire = _noop
    renew = _noop
    release = _noop
    is_locked = _noop


class EtcdLockManagerTestCase(unittest.TestCase):
    def setUp(self):
        self.client = mock.Mock(autospec=etcd.Client)
        mock_lock = mock.Mock(autospec=MockLock)
        self.lock = mock_lock()
        self.lock.key = '/test'
        self.lock.ttl = 1
        self.client.get_lock.return_value = self.lock

        _config = config.Config()
        self.lock_manager = locks.EtcdLockManager(_config, client=self.client)
        self.get_locks = self.lock_manager._locks.values

    def test_context_manager_locks(self):
        with self.lock_manager.acquire('/test'):
            self.assertEqual(len(self.get_locks()), 1)
        self.assertEqual(len(self.get_locks()), 0)

    @mock.patch('time.time', mock.MagicMock(return_value=1))
    def test_lock_does_not_renew_early(self):
        with self.lock_manager.acquire('/test'):
            time.time.return_value = 1.3
            # give the thread just enough time to run once
            time.sleep(0.01)
            lock = self.get_locks()[0]
            self.assertEqual(lock.renew.call_count, 0)

    @mock.patch('time.time', mock.MagicMock(return_value=1))
    def test_lock_does_renew(self):
        with self.lock_manager.acquire('/test'):
            time.time.return_value = 1.4
            # give the thread just enough time to run once
            time.sleep(0.01)
            lock = self.get_locks()[0]
            self.assertEqual(lock.renew.call_count, 1)

    @mock.patch('time.time', mock.MagicMock(return_value=1))
    def test_should_renew(self):
        _should_renew = self.lock_manager._should_renew
        self.lock.two_thirds_ttl = 2

        time.time.return_value = 1
        self.lock.expires_at = 4
        self.assertEqual(_should_renew(self.lock), False)

        time.time.return_value = 1
        self.lock.expires_at = 3
        self.assertEqual(_should_renew(self.lock), True)

        time.time.return_value = 1
        self.lock.expires_at = 2
        self.assertEqual(_should_renew(self.lock), True)

    @mock.patch('time.time', mock.MagicMock(return_value=1))
    def test_check_and_renew(self):
        self.lock.ttl = 3
        self.lock.expires_at = 0  # should get set in _check_and_renew
        self.lock.two_thirds_ttl = 2

        next_update = self.lock_manager._check_and_renew(self.lock)
        self.assertEqual(self.lock.renew.call_count, 1)
        self.assertEqual(self.lock.expires_at, 4)
        self.assertEqual(next_update, 2)
        self.lock.renew.reset_mock()

        self.lock.ttl = 3
        self.lock.expires_at = 5
        self.lock.two_thirds_ttl = 2

        next_update = self.lock_manager._check_and_renew(self.lock)
        self.assertEqual(self.lock.renew.call_count, 0)
        self.assertEqual(self.lock.expires_at, 5)
        self.assertEqual(next_update, 3)

    @mock.patch('time.time', mock.MagicMock(return_value=1))
    def test_check_locks(self):
        self.lock_manager._locks = {}
        next_update = self.lock_manager._check_locks()
        self.assertEqual(next_update, 61)

        self.lock.ttl = 3
        self.lock.expires_at = 4
        self.lock.two_thirds_ttl = 2
        self.lock_manager._locks = {self.lock.key: self.lock}
        next_update = self.lock_manager._check_locks()
        self.assertEqual(next_update, 2)

        self.lock.ttl = 3
        self.lock.expires_at = 5
        self.lock.two_thirds_ttl = 2
        self.lock_manager._locks = {self.lock.key: self.lock}
        next_update = self.lock_manager._check_locks()
        self.assertEqual(next_update, 3)

        self.lock.ttl = 300
        self.lock.expires_at = 0
        self.lock.two_thirds_ttl = 200
        self.lock_manager._locks = {self.lock.key: self.lock}
        next_update = self.lock_manager._check_locks()
        self.assertEqual(next_update, 61)
