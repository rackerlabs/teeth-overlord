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

from teeth_overlord.tests import TeethUnitTest

from teeth_overlord import models
from teeth_overlord.dbops import DBOps


class TestDBOps(TeethUnitTest):
    """
    Tests for the mock utilities in the TeethUnitTest base class.
    """

    def test_save(self):

        self.add_mock(models.Flavor)
        flavor = models.Flavor(name="foobar")
        ops = DBOps()

        ops.save(flavor)

        mock = self.get_mock(models.Flavor, 'save')
        mock.assert_called_once_with()

    def test_delete(self):

        self.add_mock(models.Flavor)
        flavor = models.Flavor(name="foobar")
        ops = DBOps()

        ops.delete(flavor)

        mock = self.get_mock(models.Flavor, 'delete')
        mock.assert_called_once_with()

    def test_filter(self):

        objects_mock = self.add_mock(models.Flavor)
        flavor = models.Flavor(name="foobar")
        objects_mock.return_value = [flavor]
        ops = DBOps()

        ret = ops.filter(flavor, foo="bar", fizz="buzz")

        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].name, "foobar")
        objects_mock.assert_called_once_with("filter", foo="bar", fizz="buzz")

    def test_get(self):

        objects_mock = self.add_mock(models.Flavor)
        flavor = models.Flavor(name="foobar")
        objects_mock.return_value = [flavor]
        ops = DBOps()

        ret = ops.get(flavor, foo="bar", fizz="buzz")

        self.assertEqual(ret.name, "foobar")
        objects_mock.assert_called_once_with("get", foo="bar", fizz="buzz")

    def test_all(self):

        objects_mock = self.add_mock(models.Flavor)
        flavor = models.Flavor(name="foobar")
        objects_mock.return_value = [flavor]
        ops = DBOps()

        ret = ops.all(flavor)

        self.assertEqual(len(ret), 1)
        self.assertEqual(ret[0].name, "foobar")
        objects_mock.assert_called_once_with("all")
