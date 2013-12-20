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

import collections
import json
import mock
import unittest

from cqlengine import models

from werkzeug import test
from werkzeug import wrappers

from teeth_overlord.api import public
from teeth_overlord import config as teeth_config
from teeth_overlord.jobs import base as jobs_base


class FakeQuerySet(object):
    """Rough queryset mock suitable for monkeypatching in a cqlengine model's
    'objects' attribute. Behaves roughly the same (chaining works, etc) but
    obviously skips all the db touching code.

    return_value is dumb, and any time the queryset is evaluated
    it will return whatever you pass in. (With the exception of limit(),
    which is actually implemented).

    side_effect can be a callable or exception, and will raise or call
    any time the queryset is evaluated. (ex: filter() won't trigger it,
    but all() will).
    """

    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value if return_value else []
        self.side_effect = side_effect if side_effect else None
        self._calls = []
        self._limit = None

    def __iter__(self):
        self._do_side_effect()
        return self._get_data().__iter__()

    def __repr__(self):
        return self._get_data().__repr__()

    def __len__(self):
        self._do_side_effect()
        return self._get_data().__len__()

    def __getitem__(self, item):
        self._do_side_effect()
        return self._get_data().__getitem__(item)

    def _do_side_effect(self):
        if self.side_effect:
            if issubclass(self.side_effect, Exception):
                raise self.side_effect
            elif callable(self.side_effect):
                self.side_effect()

    def _get_data(self, force_size=None):
        limit = force_size or self._limit or len(self.return_value)
        return self.return_value[:limit]

    def _find_calls(self, method):
        count = 0
        calls = []
        for call in [c for c in self._calls if c[0] == method]:
            count = count + 1
            calls.append(call)
        return (count, calls)

    def _find_calls_with_args(self, method, args, kwargs):
        count = 0
        calls = []
        (_, all_calls) = self._find_calls(method)
        for call in all_calls:
            if (call[1] == args) and (call[2] == kwargs):
                count = count + 1
                calls.append(call)
        return (count, calls)

    def call_count(self, method):
        (count, _) = self._find_calls(method)
        return count

    def call_args(self, method):
        (_, calls) = self._find_calls(method)
        return calls

    def assert_called(self, method):
        (count, _) = self._find_calls(method)
        if count == 0:
            raise AssertionError("method was not called")

    def assert_not_called(self, method):
        (count, _) = self._find_calls(method)
        if count != 0:
            raise AssertionError("method was called")

    def assert_called_once(self, method):
        (count, _) = self._find_calls(method)
        if count == 0:
            raise AssertionError("method was not called")
        if count > 1:
            raise AssertionError(
                "method was called {count} times, expected only 1".format(
                    count=count))

    def assert_called_with(self, method, *args, **kwargs):
        (count, _) = self._find_calls_with_args(method, args, kwargs)
        if count == 0:
            raise AssertionError("method was not called")

    def assert_called_once_with(self, method, *args, **kwargs):
        (count, _) = self._find_calls_with_args(method, args, kwargs)
        if count == 0:
            raise AssertionError("method was not called")
        if count > 1:
            raise AssertionError(
                "method was called {count} times, expected only 1".format(
                    count=count))

    def allow_filtering(self, *args, **kwargs):
        self._calls.append(('allow_filtering', args, kwargs))
        return self

    def all(self, *args, **kwargs):
        self._calls.append(('all', args, kwargs))
        self._do_side_effect()
        return self

    def filter(self, *args, **kwargs):
        self._calls.append(('filter', args, kwargs))
        return self

    def get(self, *args, **kwargs):
        self._calls.append(('get', args, kwargs))
        self._do_side_effect()

        # get() returns 1 thing or throws, so we want to enforce that if you
        # happen to configure the mock incorrectly.
        assert(len(self._get_data()) == 1)
        return self._get_data()[0]

    def limit(self, limit, **kwargs):
        self._calls.append(('limit', (limit,), {}))
        self._limit = limit
        return self

    def count(self, *args, **kwargs):
        self._calls.append(('count', args, kwargs))
        self._do_side_effect()
        return len(self.return_value)


class BaseAPITests(object):

    def assertModelContains(self, i1, i2):
        """Ensure all the stuff in the first instance/dict exists and is equal
        to the stuff in the second instance/dict
        """
        if isinstance(i1, models.Model):
            i1 = i2.serialize(None)
        if isinstance(i2, models.Model):
            i2 = i2.serialize(None)

        for k, v in i1.iteritems():
            self.assertEqual(v, i2[k])

    def list_some(self, model, model_objects_mock, url, mock_data):
        self.assertTrue(isinstance(mock_data[0], model))
        model_objects_mock.return_value = mock_data

        response = self.make_request('GET', url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertEqual(len(data['items']), 2)
        self.assertModelContains(data['items'][0], mock_data[0])
        self.assertModelContains(data['items'][1], mock_data[1])

    def list_none(self, model, model_objects_mock, url, mock_data):
        response = self.make_request('GET', url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['items']), 0)

    def fetch_one(self, model, model_objects_mock, url, mock_data):
        self.assertTrue(isinstance(mock_data[0], model))
        model_objects_mock.return_value = [mock_data[0]]

        response = self.make_request('GET', '{url}/{id}'.format(
            url=url,
            id=mock_data[0].id))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertModelContains(data, mock_data[0])

    def fetch_none(self, model, model_objects_mock, url, mock_data):
        model_objects_mock.side_effect = model.DoesNotExist

        response = self.make_request('GET', '{url}/{id}'.format(
            url=url,
            id='does_not_exist'))

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['message'], u'Requested object not found')

    def delete_none(self, model, model_objects_mock, url, mock_data):
        model_objects_mock.side_effect = model.DoesNotExist

        response = self.make_request('DELETE', '{url}/{id}'.format(
            url=url,
            id='does_not_exist'))

        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['message'], u'Requested object not found')
        self.assertEqual(self.get_mock(model, 'save').call_count, 0)


class TeethMockTestUtilities(unittest.TestCase):

    def setUp(self):
        self._patches = collections.defaultdict(dict)

        self.job_client_mock = mock.Mock(spec=jobs_base.JobClient)
        self.config = teeth_config.Config()
        self.public_api = public.TeethPublicAPIServer(self.config,
                                                      self.job_client_mock)

    def _get_env_builder(self, method, path, data=None, query=None):
        if data:
            data = json.dumps(data)

        return test.EnvironBuilder(method=method,
                                   path=path,
                                   data=data,
                                   content_type='application/json',
                                   query_string=query)

    def build_request(self, method, path, data=None, query=None):
        env_builder = self._get_env_builder(method, path, data, query)
        return env_builder.get_request(wrappers.BaseRequest)

    def make_request(self, method, path, data=None, query=None):
        client = test.Client(self.public_api, wrappers.BaseResponse)
        return client.open(self._get_env_builder(method, path, data, query))

    def _mock_model(self, cls, return_value=None, side_effect=None):
        """Patches a cqlengine model with a dummy queryset and a few other
        instancemethods that touch the database.

        Args:
            cls: the class to patch.
            data: optional return value of queryset operations
        Returns:
            a Mock() instance of the model's 'objects' attribute
        """
        self._mock_attr(cls, 'save', autospec=True)
        self._mock_attr(cls, 'delete', autospec=True)
        self._mock_attr(cls, 'batch')

        query = FakeQuerySet(return_value, side_effect)
        patcher = mock.patch.object(cls, 'objects', new=query)
        self._patches[cls]['objects'] = patcher.start()
        self.addCleanup(patcher.stop)

        return self.get_mock(cls, 'objects')

    def _mock_class(self, cls, return_value=None, side_effect=None,
                    autospec=False):
        """Patches a class wholesale.

        Args:
            cls: the class to patch.
        Returns:
            a Mock() instance
        """
        if cls not in self._patches:
            if isinstance(cls, basestring):
                patcher = mock.patch(cls, autospec=autospec)
            else:
                patcher = mock.patch(cls.__module__ + '.' + cls.__name__)
            self._patches[cls] = patcher.start().return_value
            self.addCleanup(patcher.stop)

        m = self.get_mock(cls)
        if return_value:
            m.return_value = return_value
        if side_effect:
            m.side_effect = side_effect
        return m

    def _mock_attr(self, cls, attr, return_value=None, side_effect=None,
                   autospec=False):
        """Patches an attribute of a class.

        Args:
            cls: the class to patch.
            attr: the attribute to patch ("some_method",
                    "some_object.some_method", etc)
            return_value: optional return_value of the mock
            side_effect: option side_effect of the mock
        Returns:
            a Mock() instance
        """
        patcher = mock.patch.object(cls, attr, autospec=autospec)
        self._patches[cls][attr] = patcher.start()
        self.addCleanup(patcher.stop)

        m = self.get_mock(cls, attr)
        if return_value:
            m.return_value = return_value
        if side_effect:
            m.side_effect = side_effect
        return m

    def add_mock(self, cls, attr=None, return_value=None, side_effect=None,
                 autospec=False):
        """Mocks a given cqlengine model, class, or attribute of a class.

        Args:
            cls: the class to patch.
            attr: the attribute of the class to patch.
            return_value: optional return_value of the mock
            side_effect: option side_effect of the mock
        Returns:
            a Mock() instance
        """
        if isinstance(cls, basestring):
            # mock a class module/name
            return self._mock_class(cls, return_value, side_effect, autospec)
        elif attr:
            # mock an arbitrary attribute of an object
            return self._mock_attr(cls,
                                   attr,
                                   return_value,
                                   side_effect,
                                   autospec)
        elif issubclass(cls, models.Model):
            # special mock for a cqlengine model
            return self._mock_model(cls, return_value, side_effect)
        else:
            # replace the class with a mock
            return self._mock_class(cls)

    def get_mock(self, cls, attr=None):
        """Returns a previously added mock.

        Args:
            cls: the class to patch.
            attr: the attribute to fetch
        Returns:
            a Mock() instance
        """
        if attr:
            return self._patches[cls][attr]
        else:
            return self._patches[cls]


class TeethAPITestCase(TeethMockTestUtilities, BaseAPITests):
    pass
