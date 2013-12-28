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

import statsd

from teeth_overlord import config as teeth_config
from teeth_overlord import stats


class SpecificException(Exception):
    pass


class SomeClass(object):
    def __init__(self, config, stats_client):
        self.stats_client = stats_client

    @stats.incr_stat('somestat')
    def success_func(self):
        pass

    @stats.incr_stat('somestat')
    def error_func(self):
        raise SpecificException


class StatsClientTestCase(unittest.TestCase):

    def setUp(self):
        self.config = teeth_config.Config()
        self.config.STATSD_PREFIX = 'teeth'
        self.mock_stats_client = mock.Mock(spec=statsd.StatsClient)
        self.some_object = SomeClass(self.config, self.mock_stats_client)

    def test_get_stats_client_with_no_prefix(self):
        client = stats.get_stats_client(self.config)
        self.assertEqual(client._prefix, 'teeth')

    def test_get_stats_client_with_prefix(self):
        client = stats.get_stats_client(self.config, prefix='api')
        self.assertEqual(client._prefix, 'teeth.api')

    def test_success_incrs_success_stat(self):
        self.some_object.success_func()
        self.mock_stats_client.incr.assert_called_once_with('somestat.success')

    def test_error_incrs_error_stat(self):
        self.assertRaises(SpecificException, self.some_object.error_func)
        self.mock_stats_client.incr.assert_called_once_with('somestat.error')


class ConcurrencyGaugeTestCase(unittest.TestCase):
    def test_concurrency_guage(self):
        mock_stats_client = mock.Mock(spec=statsd.StatsClient)
        concurrency_gauge = stats.ConcurrencyGauge(mock_stats_client, 'foo')

        with concurrency_gauge:
            mock_stats_client.gauge.assertCalledOnceWith('foo', 1)
            mock_stats_client.gauge.reset_mock()

            with concurrency_gauge:
                mock_stats_client.gauge.assertCalledOnceWith('foo', 2)
                mock_stats_client.gauge.reset_mock()

            mock_stats_client.gauge.assertCalledOnceWith('foo', 1)
            mock_stats_client.gauge.reset_mock()

        mock_stats_client.gauge.assertCalledOnceWith('foo', 0)
