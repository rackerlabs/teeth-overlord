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

from teeth_overlord import locks


class DictLockManagerTestCase(unittest.TestCase):
    def setUp(self):
        self.lock_manager = locks.DictLockManager()

    def test_lock(self):
        asset = '/chassis/chassis_id'
        self.lock_manager.lock(asset)
        self.assertEqual(self.lock_manager.is_locked(asset), True)

    def test_lock_already_locked(self):
        asset = '/chassis/chassis_id'
        self.lock_manager.lock(asset)
        self.assertEqual(self.lock_manager.is_locked(asset), True)
        self.assertRaises(locks.AssetLockedError,
                          self.lock_manager.lock,
                          asset)

    def test_unlock(self):
        asset = '/chassis/chassis_id'
        self.lock_manager.lock(asset)
        self.assertEqual(self.lock_manager.is_locked(asset), True)
        self.lock_manager.unlock(asset)
        self.assertEqual(self.lock_manager.is_locked(asset), False)
