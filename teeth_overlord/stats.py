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

import statsd


class NoopStatsClient(object):
    def _noop(self, *args, **kwargs):
        pass

    incr = _noop
    decr = _noop
    timing = _noop
    gauge = _noop
    set = _noop

    # TODO(jimrollenhagen) implement timer (context manager and decorater)
    # TODO(jimrollenhagen) implement pipeline noop (context manager and method)
    # TODO(jimrollenhagen) implement send (method, sends pipelined commands)
    # (we aren't using any of these yet)


def get_stats_client(config, prefix=None):
    """Gets statsd client with additional prefix.
    For example, if the config prefix is 'teeth' and 'api' is passed in,
    the prefix would be teeth.api.
    """
    if prefix is not None:
        prefix = '{0}.{1}'.format(config.STATSD_PREFIX, prefix)
    else:
        prefix = config.STATSD_PREFIX

    if not config.STATSD_ENABLED:
        return NoopStatsClient()

    return statsd.StatsClient(config.STATSD_HOST,
                              config.STATSD_PORT,
                              prefix=prefix)


def incr_stat(key):
    """Decorator that increments a stat with the given key. Decorated function
    must be a bound method on a class that has a stats_client attribute.
    """
    # TODO(jimrollenhagen) what about the case where e.g. no chassis available
    # to create an instance?  this won't raise an exception (right?), but
    # should it be counted as a success?

    def incr_decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            client = self.stats_client
            try:
                ret = func(self, *args, **kwargs)
            except Exception:
                client.incr('{}.error'.format(key))
                raise
            else:
                client.incr('{}.success'.format(key))
                return ret
        return wrapper
    return incr_decorator
