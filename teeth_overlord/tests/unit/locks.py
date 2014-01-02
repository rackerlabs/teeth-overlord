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

from teeth_overlord import config
from teeth_overlord import locks


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
        self.mock_lock = mock.Mock(autospec=MockLock)
        self.lock = self.mock_lock()
        self.lock.key = '/test'
        self.lock.ttl = 1
        self.client.get_lock.return_value = self.lock
        #self.client.get_lock.return_value = MockLock('/test', ttl=1)
        _config = config.Config()
        self.lock_manager = locks.EtcdLockManager(_config, client=self.client)
        self.get_locks = self.lock_manager._locks.values

    def tearDown(self):
        self.lock_manager.stop()

    @mock.patch('time.time', mock.MagicMock(return_value=1))
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
            lock = self.lock_manager._locks.values()[0]
            self.assertEqual(lock.renew.call_count, 0)

    @mock.patch('time.time', mock.MagicMock(return_value=1))
    def test_lock_does_renew(self):
        with self.lock_manager.acquire('/test'):
            time.time.return_value = 1.4
            # give the thread just enough time to run once
            time.sleep(0.01)
            lock = self.lock_manager._locks.values()[0]
            self.assertEqual(lock.renew.call_count, 1)
