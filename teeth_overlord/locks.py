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

import etcd


class AssetLockedError(Exception):
    pass


def _lock_key(asset):
    return '/locks{}'.format(asset)


class DictLockManager(object):
    def __init__(self):
        self.client = {}

    def lock(self, asset):
        """Set a lock for an asset."""
        key = _lock_key(asset)
        if self.client.get(key):
            raise AssetLockedError
        self.client[key] = True

    def unlock(self, asset):
        """Clear a lock for an asset"""
        key = _lock_key(asset)
        if key in self.client:
            del self.client[key]


class EtcdLockManager(object):
    def __init__(self, config):
        self.client = etcd.Client(config.ETCD_HOST, config.ETCD_PORT)

    def lock(self, asset):
        """Set a lock for an asset."""
        key = _lock_key(asset)

        if self.client.get(key):
            raise AssetLockedError

        self.client.set(key, True)

    def unlock(self, asset):
        """Clear a lock for an asset"""
        key = _lock_key(asset)
        self.client.delete(key)


def get_lock_manager(config):
    if not config.ENABLE_ETCD:
        return DictLockManager()
    return EtcdLockManager(config)
