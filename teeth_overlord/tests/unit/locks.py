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

import unittest

from teeth_overlord import config as teeth_config
from teeth_overlord import locks


class MockEtcdClient(object):
    """etcd client for testing that acts (almost)like the real thing.

    Currently just mocks get/set/delete for a leaf node, as that's all
    we are using right now.
    """

    def __init__(self):
        self.datastore = {}

    def get(self, key):
        """Gets a value for given key.

        If key exists, returns value.
        If not, raises a KeyError.
        """
        return self.datastore[key]

    def set(self, key, value):
        """Sets a value for a given key."""
        self.datastore[key] = value

    def delete(self, key):
        """Deletes a given key.

        If key does not exist, raises a KeyError.
        """
        del self.datastore[key]


class LockManagerBaseTestCase(object):
    def _lock_with_lock_manager(self):
        self.lock_manager.lock(self.asset)
        self.assertEqual(self.lock_manager.is_locked(self.asset), True)

    def _lock_and_unlock_with_context_manager(self):
        with self.lock_manager.get_lock(self.asset):
            self.assertEqual(self.lock_manager.is_locked(self.asset), True)

    def test_lock(self):
        self._lock_with_lock_manager()

    def test_lock_already_locked(self):
        self._lock_with_lock_manager()
        self.assertRaises(locks.AssetLockedError,
                          self.lock_manager.lock,
                          self.asset)

    def test_unlock(self):
        self._lock_with_lock_manager()
        self.lock_manager.unlock(self.asset)
        self.assertEqual(self.lock_manager.is_locked(self.asset), False)

    def test_lock_two_assets(self):
        self._lock_with_lock_manager()
        self.lock_manager.lock(self.asset_two)
        self.assertEqual(self.lock_manager.is_locked(self.asset_two), True)

    def test_lock_context_manager(self):
        self._lock_and_unlock_with_context_manager()
        self.assertEqual(self.lock_manager.is_locked(self.asset), False)

    def test_lock_context_manager_already_locked(self):
        self._lock_with_lock_manager()
        self.assertRaises(locks.AssetLockedError,
                          self._lock_and_unlock_with_context_manager)
        # make sure asset is still locked
        self.assertEqual(self.lock_manager.is_locked(self.asset), True)


class DictLockManagerTestCase(LockManagerBaseTestCase, unittest.TestCase):
    def setUp(self):
        self.lock_manager = locks.DictLockManager()
        self.asset = '/chassis/chassis_id'
        self.asset_two = '/chassis/chassis_id_two'


class EtcdLockManagerTestCase(LockManagerBaseTestCase, unittest.TestCase):
    def setUp(self):
        config = teeth_config.Config()
        mock_client = MockEtcdClient()
        self.lock_manager = locks.EtcdLockManager(config, client=mock_client)
        self.asset = '/chassis/chassis_id'
        self.asset_two = '/chassis/chassis_id_two'

    def tearDown(self):
        self.lock_manager.unlock(self.asset)
        self.lock_manager.unlock(self.asset_two)
