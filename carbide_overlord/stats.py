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
import threading

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


class ConcurrencyGauge(object):
    """A context manager which emits a gauge metric indicating how many
    concurrent active contexts it is in use by. For example, to measure how
    many calls to `do_long_running_work()` are executing concurrently from a
    given location::

        with a_concurrency_gauge:
            do_long_running_work()

    It would generally not make sense to have two guages with the same name, as
    they would tend to overwrite each other's values.

    (Also, one could do this by specifying "delta" values to a statsd gauge,
    but doing so is failure-prone without some sort of "checkpointing" to
    account for packet loss or even just process restarts).
    """
    def __init__(self, client, name):
        self.value = 0
        self.lock = threading.Lock()
        self.client = client
        self.name = name

    def __enter__(self):
        with self.lock:
            self.value += 1

        self.client.gauge(self.name, self.value)

    def __exit__(self, type, value, traceback):
        with self.lock:
            self.value -= 1

        self.client.gauge(self.name, self.value)


def get_stats_client(config, prefix=None):
    """Gets statsd client with additional prefix.
    For example, if the config prefix is 'carbide' and 'api' is passed in,
    the prefix would be carbide.api.
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
