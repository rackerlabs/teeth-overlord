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

import functools

from statsd import StatsClient


def get_stats_client(config):
    return StatsClient(config.STATSD_HOST, config.STATSD_PORT, prefix=config.STATSD_PREFIX)


def incr_stat(key):
    """
    Decorator that increments a stat with the given key.
    Decorated function must be a bound method on a class that has a stats_client attribute.
    """
    # TODO what about the case where e.g. no chassis available to create an instance?
    # this won't raise an exception (right?), but should it be counted as a success?

    def incr_decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            client = self.stats_client
            try:
                ret = func(self, *args, **kwargs)
            except:
                client.incr('{}.error'.format(key))
                raise
            else:
                client.incr('{}.success'.format(key))
                return ret
        return wrapper
    return incr_decorator
