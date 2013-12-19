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

from teeth_overlord.tests import TeethMockTestUtilities

from teeth_overlord.jobs.base import JobClient
from teeth_overlord import models


class TestModelMock(TeethMockTestUtilities):
    """Tests for the mock utilities in the TeethUnitTest base class."""

    def test_mock_class(self):

        mock = self.add_mock(JobClient)
        mock.submit_job.return_value = 42

        # re-import JobClient so the patch is picked up. You probably shouldn't do
        # this if you can help it.
        from teeth_overlord.jobs.base import JobClient as TestJobClient
        client = TestJobClient("stuff")
        ret = client.submit_job("jobstuff")

        mock.submit_job.assert_called_once_with("jobstuff")
        self.assertEqual(ret, 42)

    def test_mock_method(self):

        mock = self.add_mock(models.Flavor, "save", "save_return")

        model = models.Flavor(name="flavor")
        ret = model.save()

        self.assertEqual(ret, "save_return")
        mock.assert_called_once_with()

    def test_mock_model(self):

        self.add_mock(models.Flavor, return_value=["filter_return"])

        mock = self.get_mock(models.Flavor, "objects")

        model = models.Flavor(name="flavor")
        ret = list(model.objects.filter())
        ret2 = list(model.objects.limit(100).filter(1))

        self.assertTrue(ret == ret2 == ["filter_return"])
        mock.assert_called_once_with("filter", 1)
        mock.assert_called_once_with("filter")

    def test_add_mock_model_objects(self):

        self.add_mock(models.JobRequest, "get", "get_return")

        mock = self.get_mock(models.JobRequest, "get")

        model = models.JobRequest(job_type="jobrequest")
        ret = model.get()

        self.assertEqual(ret, "get_return")
        mock.assert_called_once_with()

    def test_add_mock_superclass_method(self):

        mock = self.add_mock(models.JobRequest, "save")
        mock.return_value = "save_return"

        model = models.JobRequest(job_type="jobrequest")
        ret = model.save()

        self.assertEqual(ret, "save_return")
        self.get_mock(models.JobRequest, "save").assert_called_once_with()

    def test_add_mock_instance_method(self):

        mock = self.add_mock(models.JobRequest, "touch")
        mock.return_value = "touch_return"

        model = models.JobRequest(job_type="jobrequest")
        ret = model.touch()

        self.assertEqual(ret, "touch_return")
        self.get_mock(models.JobRequest, "touch").assert_called_once_with()

    def test_mock_missing_attribute_fails(self):

        self.assertRaises(AttributeError, self.add_mock, models.JobRequest, "foo.bar")
        self.assertRaises(AttributeError, self.add_mock, models.JobRequest, "foobar")
