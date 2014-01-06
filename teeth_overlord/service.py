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

import signal
import threading
import traceback

from cqlengine import connection
import structlog

from teeth_overlord import settings

# Sometimes global setup is necessary. Make sure that if we try to do it twice:
#   a. We don't actually do it twice
#   b. The same config is used
_global_config = None

EXCEPTION_LOG_METHODS = ['error']


def _capture_stack_trace(logger, method, event):
    if method in EXCEPTION_LOG_METHODS:
        event['exception'] = traceback.format_exc()

    return event


def global_setup(config):
    """Perform global cofiguration. In a given process, this should only
    ever be called with a single configuration instance. Doing otherwise
    will result in a runtime exception.
    """
    global _global_config
    if _global_config is None:
        _global_config = config
        connection.setup(config.CASSANDRA_CLUSTER,
                         consistency=config.CASSANDRA_CONSISTENCY)

        processors = [
            _capture_stack_trace,
        ]

        if config.PRETTY_LOGGING:
            processors.append(structlog.processors.ExceptionPrettyPrinter())
            processors.append(structlog.processors.KeyValueRenderer())
        else:
            processors.append(structlog.processors.JSONRenderer())

        structlog.configure(
            processors=processors
        )
    elif _global_config != config:
        raise Exception('global_setup called twice with different '
                        'configurations')


class TeethServiceRunner(object):
    """Instantiate and run a SynchronousTeethService."""

    def __init__(self, service_class):
        self.service = service_class(settings.get_config())
        self.signal_map = {
            signal.SIGTERM: self._terminate,
            signal.SIGINT: self._terminate,
        }

    def run(self):
        """Run the service."""
        for signum, handler in self.signal_map.iteritems():
            signal.signal(signum, handler)

        self.service.run()

    def _terminate(self, signum, frame):
        self.service.stop()


class SynchronousTeethService(object):
    """Base class for all Teeth services."""
    def __init__(self, config):
        self.config = config
        self.stopping = threading.Event()

    def run(self):
        """Run the service to completion."""
        global_setup(self.config)
        self.stopping.clear()

    def stop(self):
        """Attempt to gracefully stop."""
        self.stopping.set()
