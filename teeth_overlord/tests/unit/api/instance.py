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

import json

from teeth_overlord.api import public
from teeth_overlord import errors
from teeth_overlord import models
from teeth_overlord import tests


class TestInstanceAPI(tests.TeethAPITestCase):

    def setUp(self):
        super(TestInstanceAPI, self).setUp()

        self.url = '/v1/instances'

        self.instance_objects_mock = self.add_mock(models.Instance)
        self.instance1 = models.Instance(id='instance1',
                                         name='instance1_name',
                                         flavor_id='flavor1',
                                         image_id='image1',
                                         chassis_id='chassis1',
                                         state=models.InstanceState.ACTIVE)
        self.instance2 = models.Instance(id='instance2',
                                         name='instance2_name',
                                         flavor_id='flavor2',
                                         image_id='image2',
                                         chassis_id='chassis2',
                                         state=models.InstanceState.DELETED)

        # hardcoded valid imageid from the static image provider
        self.valid_image_id = '8226c769-3739-4ee6-921c-82110da6c669'

    def test_admin_pass_not_string(self):
        metadata = {
            'admin_pass': 0,
            'public_keys': {'key_name': 'key_data'},
            'meta': {'valid': 'meta'}
        }
        self.assertRaises(errors.InvalidParametersError,
                          public._validate_metadata,
                          metadata,
                          self.config)

    def test_public_keys_not_dict(self):
        metadata = {
            'admin_pass': 'password',
            'public_keys': 0,
            'meta': {'valid': 'meta'}
        }
        self.assertRaises(errors.InvalidParametersError,
                          public._validate_metadata,
                          metadata,
                          self.config)

    def test_meta_not_dict(self):
        metadata = {
            'admin_pass': 'password',
            'public_keys': {'key_name': 'key_data'},
            'meta': 0
        }
        self.assertRaises(errors.InvalidParametersError,
                          public._validate_metadata,
                          metadata,
                          self.config)

    def test_meta_too_big(self):
        self.config.MAX_USER_METADATA_SIZE = 1
        metadata = {
            'admin_pass': 'password',
            'public_keys': {'key_name': 'key_data'},
            'meta': {'too': 'many', 'keys': 'here'}
        }
        self.assertRaises(errors.InvalidParametersError,
                          public._validate_metadata,
                          metadata,
                          self.config)

    def test_validate_metadata(self):
        metadata = {
            'admin_pass': 'password',
            'public_keys': {'key_name': 'key_data'},
            'meta': {'valid': 'meta'}
        }
        public._validate_metadata(metadata, self.config)

    def test_admin_pass_optional(self):
        metadata = {
            'public_keys': {'key_name': 'key_data'},
            'meta': {'valid': 'meta'}
        }
        public._validate_metadata(metadata, self.config)

    def test_files_not_dict(self):
        files = 0
        self.assertRaises(errors.InvalidParametersError,
                          public._validate_files,
                          files,
                          self.config)

    def test_too_many_files(self):
        self.config.MAX_INSTANCE_FILES = 1
        files = {'file1': 'blah', 'file2': 'blah'}
        self.assertRaises(errors.InvalidParametersError,
                          public._validate_files,
                          files,
                          self.config)

    def test_file_too_big(self):
        self.config.MAX_INSTANCE_FILE_SIZE = 1
        files = {'file1': 'blah'}
        self.assertRaises(errors.InvalidParametersError,
                          public._validate_files,
                          files,
                          self.config)

    def test_file_bad_base64(self):
        files = {'file1': 'bla'}
        self.assertRaises(errors.InvalidParametersError,
                          public._validate_files,
                          files,
                          self.config)

    def test_validate_files(self):
        files = {'file1': 'blah'}
        public._validate_files(files, self.config)

    def test_list_instances_some(self):
        self.list_some(models.Instance,
                       self.instance_objects_mock,
                       self.url,
                       [self.instance1, self.instance2])

    def test_list_instances_none(self):
        self.list_none(models.Instance,
                       self.instance_objects_mock,
                       self.url,
                       [self.instance1, self.instance2])

    def test_fetch_instance_one(self):
        self.fetch_one(models.Instance,
                       self.instance_objects_mock,
                       self.url,
                       [self.instance1, self.instance2])

    def test_fetch_instance_none(self):
        self.fetch_none(models.Instance,
                        self.instance_objects_mock,
                        self.url,
                        [self.instance1, self.instance2])

    def test_delete_instance_none(self):
        self.delete_none(models.Instance,
                         self.instance_objects_mock,
                         self.url,
                         [self.instance1, self.instance2])

    def test_create_instance(self):
        return_value = [models.Flavor(id='flavor', name='some_flavor')]
        self.add_mock(models.Flavor, return_value=return_value)

        metadata = {
            'admin_pass': 'password',
            'public_keys': {
                'key_name': 'key_data'
            },
            'meta': {
                'some': 'data',
            },
            'name': 'created_instance',
            'hostname': 'createdinstance',
            'availability_zone': 'teeth'
        }
        data = {
            'name': 'created_instance',
            'flavor_id': 'flavor',
            'image_id': self.valid_image_id,
            'admin_pass': metadata['admin_pass'],
            'ssh_keys': metadata['public_keys'],
            'user_metadata': metadata['meta'],
        }

        response = self.make_request('POST', self.url, data=data)

        # get the saved instance
        save_mock = self.get_mock(models.Instance, 'save')
        self.assertEqual(save_mock.call_count, 1)
        instance = save_mock.call_args[0][0]

        self.assertEqual(instance.name, 'created_instance')
        self.assertEqual(instance.flavor_id, 'flavor')
        self.assertEqual(instance.image_id, self.valid_image_id)

        self.job_client_mock.submit_job.assert_called_once_with(
            'instances.create',
            instance_id=instance.id,
            metadata=metadata,
            files={})

        self.assertEqual(response.status_code, 201)

        expected_location = 'http://localhost{url}/{id}'.format(url=self.url,
                                                                id=instance.id)
        self.assertEqual(response.headers['Location'], expected_location)

    def test_create_instance_deleted_flavor(self):
        self.add_mock(models.Flavor,
                      return_value=[models.Flavor(id='flavor',
                                                  name='some_flavor',
                                                  deleted=True)])

        response = self.make_request('POST', self.url,
                                     data={'name': 'test_instance',
                                           'flavor_id': 'flavor',
                                           'image_id': self.valid_image_id})

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid request body')
        self.assertTrue('Flavor is deleted' in data['details'])

    def test_create_instance_missing_data(self):
        return_value = [models.Flavor(id='flavor', name='some_flavor')]
        self.add_mock(models.Flavor, return_value=return_value)

        response = self.make_request('POST', self.url,
                                     data={'flavor_id': 'flavor',
                                           'image_id': self.valid_image_id})

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid request body')

    def test_create_instance_bad_flavor(self):

        self.add_mock(models.Flavor, side_effect=models.Flavor.DoesNotExist)

        response = self.make_request('POST', self.url,
                                     data={'name': 'created_instance',
                                           'flavor_id': 'flavor',
                                           'image_id': self.valid_image_id})

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['message'], 'Invalid request body')

    def test_create_instance_bad_image(self):

        pass

        # TODO(morgabra): Current fake image provider always works
        #return_value = [models.Flavor(id='flavor', name='flavor')]
        #self.add_mock(models.Flavor, return_value=return_value)

        #response = self.make_request('POST', self.url,
        #                             data={"name": "created_instance",
        #                                   "flavor_id": "flavor",
        #                                   "image_id": "does_not_exist"})

        #data = json.loads(response.data)
        #self.assertEqual(response.status_code, 400)
        #self.assertEqual(data['message'], 'Image not found')

    def test_create_instance_bad_metadata(self):
        return_value = [models.Flavor(id='flavor', name='some_flavor')]
        self.add_mock(models.Flavor, return_value=return_value)

        data = {
            'name': 'created_instance',
            'flavor_id': 'flavor',
            'image_id': self.valid_image_id,
            'admin_pass': 'password',
            'ssh_keys': 'keys as string!'
        }

        response = self.make_request('POST', self.url, data=data)
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)

    def test_create_instance_bad_files(self):
        return_value = [models.Flavor(id='flavor', name='some_flavor')]
        self.add_mock(models.Flavor, return_value=return_value)

        data = {
            'name': 'created_instance',
            'flavor_id': 'flavor',
            'image_id': self.valid_image_id,
            'admin_pass': 'password',
            'files': {'/etc/hosts': 'bla'}
        }

        response = self.make_request('POST', self.url, data=data)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)

    def test_delete_instance(self):
        self.instance_objects_mock.return_value = [self.instance1]

        response = self.make_request('DELETE',
                                     '{url}/foobar'.format(url=self.url))

        self.assertEqual(response.status_code, 204)
        self.instance_objects_mock.assert_called_once_with('get', id='foobar')
        self.job_client_mock.submit_job.assert_called_once_with(
            'instances.delete',
            instance_id='instance1')

        save_mock = self.get_mock(models.Instance, 'save')
        self.assertEqual(save_mock.call_count, 1)
        self.assertEqual(self.instance1.state, models.InstanceState.DELETING)

    def test_delete_instance_already_deleted(self):
        self.instance_objects_mock.return_value = [self.instance2]

        response = self.make_request('DELETE',
                                     '{url}/foobar'.format(url=self.url))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.instance2.state, models.InstanceState.DELETED)

        self.instance2.state = models.InstanceState.DELETING
        response = self.make_request('DELETE',
                                     '{url}/foobar'.format(url=self.url))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.instance2.state, models.InstanceState.DELETING)

    def test_delete_instance_does_not_exist(self):
        self.instance_objects_mock.side_effect = models.Instance.DoesNotExist

        response = self.make_request('DELETE',
                                     '{url}/foobar'.format(url=self.url))

        self.assertEqual(response.status_code, 404)
