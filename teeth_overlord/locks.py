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


class Lock(object):
    """Context manager to get a lock."""
    def __init__(self, manager, asset):
        self.manager = manager
        self.asset = asset

    def __enter__(self):
        self.manager.lock(self.asset)

    def __exit__(self, type, value, traceback):
        if type is None:
            self.manager.unlock(self.asset)


class BaseLockManager(object):
    def __init__(self):
        raise NotImplementedError

    def lock(self, asset):
        raise NotImplementedError

    def unlock(self, asset):
        raise NotImplementedError

    def is_locked(self, asset):
        raise NotImplementedError


class DictLockManager(BaseLockManager):
    def __init__(self):
        self.client = {}

    def lock(self, asset):
        """Set a lock for an asset."""
        if self.is_locked(asset):
            raise AssetLockedError

        key = _lock_key(asset)
        self.client[key] = True

    def unlock(self, asset):
        """Clear a lock for an asset."""
        key = _lock_key(asset)
        if key in self.client:
            del self.client[key]

    def is_locked(self, asset):
        """Check if an asset is locked."""
        key = _lock_key(asset)
        return self.client.get(key) is not None


class EtcdLockManager(BaseLockManager):
    def __init__(self, config):
        self.client = etcd.Client(config.ETCD_HOST, config.ETCD_PORT)

    def lock(self, asset):
        """Set a lock for an asset."""
        if self.is_locked(asset):
            raise AssetLockedError

        key = _lock_key(asset)
        self.client.set(key, True)

    def unlock(self, asset):
        """Clear a lock for an asset."""
        key = _lock_key(asset)
        try:
            self.client.delete(key)
        except KeyError:
            # already unlocked
            pass

    def is_locked(self, asset):
        """Check if an asset is locked."""
        key = _lock_key(asset)
        try:
            self.client.get(key)
            return True
        except KeyError:
            return False


def get_lock_manager(config):
    if not config.ENABLE_ETCD:
        return DictLockManager()
    return EtcdLockManager(config)
