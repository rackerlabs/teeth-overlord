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

import mock
import unittest

from statsd import StatsClient

from teeth_overlord.config import Config
from teeth_overlord.stats import get_stats_client, incr_stat


class SomeClass(object):
    def __init__(self, config, stats_client):
        self.stats_client = stats_client

    @incr_stat('somestat')
    def success_func(self):
        pass

    @incr_stat('somestat')
    def error_func(self):
        raise Exception


class StatsClientTestCase(unittest.TestCase):

    def setUp(self):
        self.config = Config()
        self.config.STATSD_PREFIX = 'teeth'
        self.mock_stats_client = mock.Mock(spec=StatsClient)
        self.some_object = SomeClass(self.config, self.mock_stats_client)

    def test_get_stats_client_with_no_prefix(self):
        client = get_stats_client(self.config)
        self.assertEquals(client._prefix, 'teeth')

    def test_get_stats_client_with_prefix(self):
        client = get_stats_client(self.config, prefix='api')
        self.assertEquals(client._prefix, 'teeth.api')

    def test_success_incrs_success_stat(self):
        self.some_object.success_func()
        self.some_object.stats_client.incr.assert_called_once_with('somestat.success')

    def test_error_incrs_error_stat(self):
        try:
            self.some_object.error_func()
        except:
            # expecting this
            pass
        self.some_object.stats_client.incr.assert_called_once_with('somestat.error')
