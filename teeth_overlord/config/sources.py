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

import os
import etcd


class ConfigSource(object):
    """Base configuration source class.

    Used for fetching configuration keys from external sources.
    """
    def __init__(self, conf, *args):
        self._conf = conf

    def get(self, key):
        """Return a value for a given key"""
        raise NotImplementedError


class EnvSource(ConfigSource):
    """Replaces settings with values from os.environ."""

    def get(self, key):
        return os.environ.get(key, None)


class EtcdSource(ConfigSource):
    """Replaces settings with values from etcd."""

    def __init__(self, conf, host_key, port_key, dir_key):
        super(EtcdSource, self).__init__(conf)
        self._host = self._conf[host_key]
        self._port = self._conf[port_key]
        self._dir = self._conf[dir_key]
        self._client = etcd.Client(host=self._host, port=self._port)

    def _mkpath(self, key):
        return "{}/{}".format(self._dir, key)

    def get(self, key):
        try:
            return self._client.get(self._mkpath(key)).value
        except KeyError:
            pass
