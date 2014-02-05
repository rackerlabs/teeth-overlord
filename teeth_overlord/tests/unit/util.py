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

from teeth_overlord import util


class TestIntervalTimer(unittest.TestCase):
    @mock.patch('time.sleep')
    def test_no_error_no_event(self, mocked_sleep):
        t = util.IntervalTimer(1, 10, backoff_factor=5, jitter=.1)

        t.wait()
        self.assertEqual(t.next_interval, t.base_interval)
        mocked_sleep.assert_called_once_with(1)

        event = mock.Mock()
        t.wait(event=event)
        self.assertEqual(t.next_interval, t.base_interval)
        event.wait.assert_called_once_with(1)

    def test_no_error_with_event(self):
        t = util.IntervalTimer(1, 10, backoff_factor=5, jitter=.1)

        event = mock.Mock()
        t.wait(event=event)
        self.assertEqual(t.next_interval, t.base_interval)
        event.wait.assert_called_once_with(1)

    @mock.patch('random.normalvariate')
    def test_error_flow(self, mocked_normalvariate):
        t = util.IntervalTimer(1, 10, backoff_factor=5, jitter=.1)
        mocked_normalvariate.return_value = 5.5
        event = mock.Mock()

        t.wait(event=event, error=True)
        mocked_normalvariate.assert_called_once_with(5, .5)
        self.assertEqual(t.next_interval, 5.5)
        event.wait.assert_called_once_with(5.5)

        mocked_normalvariate.reset_mock()
        event.wait.reset_mock()
        mocked_normalvariate.return_value = 12
        t.wait(event=event, error=True)
        mocked_normalvariate.assert_called_once_with(10, 1.0)
        self.assertEqual(t.next_interval, 12)
        event.wait.assert_called_once_with(12)

        event.wait.reset_mock()
        t.wait(event=event)
        self.assertEqual(t.next_interval, 1)
        event.wait.assert_called_once_with(1)
