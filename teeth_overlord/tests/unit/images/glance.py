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
import glanceclient
from glanceclient import exc as glance_exceptions

from keystoneclient.apiclient import exceptions as keystone_exceptions
from keystoneclient.v2_0 import client as keystoneclient

import hmac
import mock
import time

from teeth_overlord import config
from teeth_overlord.images import glance
from teeth_overlord import tests


FAKE_IMAGES_RESPONSE = [
    {
        u'status': u'active',
        u'tags': [],
        u'kernel_id': u'b134ff0b-1d27-48d5-9a5b-fbd0c1f559cc',
        u'container_format': u'ami',
        u'min_ram': 0,
        u'ramdisk_id': u'a45a26c5-2813-4b15-9220-180c581bf16c',
        u'updated_at': u'2014-01-10T18:53:24Z',
        u'visibility': u'public',
        u'file': u'/v2/images/cab0fa89-4bcc-41d2-b500-3642c544d174/file',
        u'min_disk': 0,
        u'id': u'cab0fa89-4bcc-41d2-b500-3642c544d174',
        u'size': 25165824,
        u'name': u'cirros-0.3.1-x86_64-uec',
        u'checksum': u'f8a2eeee2dc65b3d9b6e63678955bd83',
        u'created_at': u'2014-01-10T18:53:24Z',
        u'disk_format': u'ami',
        u'protected': False,
        u'schema': u'/v2/schemas/image'
    },
    {
        u'status': u'active',
        u'tags': [],
        u'container_format': u'ari',
        u'min_ram': 0,
        u'updated_at': u'2014-01-10T18:53:24Z',
        u'visibility': u'public',
        u'file': u'/v2/images/a45a26c5-2813-4b15-9220-180c581bf16c/file',
        u'min_disk': 0,
        u'id': u'a45a26c5-2813-4b15-9220-180c581bf16c',
        u'size': 3714968,
        u'name': u'cirros-0.3.1-x86_64-uec-ramdisk',
        u'checksum': u'69c33642f44ca552ba4bb8b66ad97e85',
        u'created_at': u'2014-01-10T18:53:24Z',
        u'disk_format': u'ari',
        u'protected': False,
        u'schema': u'/v2/schemas/image'
    },
    {
        u'status': u'active',
        u'tags': [],
        u'container_format': u'aki',
        u'min_ram': 0,
        u'updated_at': u'2014-01-10T18:53:23Z',
        u'visibility': u'public',
        u'file': u'/v2/images/b134ff0b-1d27-48d5-9a5b-fbd0c1f559cc/file',
        u'min_disk': 0,
        u'id': u'b134ff0b-1d27-48d5-9a5b-fbd0c1f559cc',
        u'size': 4955792,
        u'name': u'cirros-0.3.1-x86_64-uec-kernel',
        u'checksum': u'c352f4e7121c6eae958bc1570324f17e',
        u'created_at': u'2014-01-10T18:53:23Z',
        u'disk_format': u'aki',
        u'protected': False,
        u'schema': u'/v2/schemas/image'
    }
]

FAKE_IMAGE_INFO = [
    collections.OrderedDict([
        ('id', u'cab0fa89-4bcc-41d2-b500-3642c544d174'),
        ('name', u'cirros-0.3.1-x86_64-uec'),
        ('urls', [('http://10.127.75.253:8080/v1/AUTH_tenant/glance/') +
                  ('cab0fa89-4bcc-41d2-b500-3642c544d174?temp_url_sig=') +
                  ('4a23aaec863f1bd0974d4e83910d3e17&temp_url_expires=3642')]),
        ('hashes', {'md5': u'f8a2eeee2dc65b3d9b6e63678955bd83'})
    ]),
    collections.OrderedDict([
        ('id', u'a45a26c5-2813-4b15-9220-180c581bf16c'),
        ('name', u'cirros-0.3.1-x86_64-uec-ramdisk'),
        ('urls', [('http://10.127.75.253:8080/v1/AUTH_tenant/glance/') +
                  ('a45a26c5-2813-4b15-9220-180c581bf16c?temp_url_sig=') +
                  ('4a23aaec863f1bd0974d4e83910d3e17&temp_url_expires=3642')]),
        ('hashes', {'md5': u'69c33642f44ca552ba4bb8b66ad97e85'})
    ]),
    collections.OrderedDict([
        ('id', u'b134ff0b-1d27-48d5-9a5b-fbd0c1f559cc'),
        ('name', u'cirros-0.3.1-x86_64-uec-kernel'),
        ('urls', [('http://10.127.75.253:8080/v1/AUTH_tenant/glance/') +
                  ('b134ff0b-1d27-48d5-9a5b-fbd0c1f559cc?temp_url_sig=') +
                  ('4a23aaec863f1bd0974d4e83910d3e17&temp_url_expires=3642')]),
        ('hashes', {'md5': u'c352f4e7121c6eae958bc1570324f17e'})
    ])
]


class TestGlanceProvider(tests.TeethMockTestUtilities):

    def setUp(self):
        super(TestGlanceProvider, self).setUp()

        self.config = config.LazyConfig(config={
            'KEYSTONE_USER': 'user',
            'KEYSTONE_PASS': 'pass',
            'KEYSTONE_TENANT_ID': 'tenant',
            'KEYSTONE_AUTH_URL': 'auth_url',
            'GLANCE_VERSION': '2',
            'GLANCE_URL': 'glance_url',
            'GLANCE_SWIFT_CONTAINER': 'glance',
            'SWIFT_URL': 'http://10.127.75.253:8080/',
            'SWIFT_TEMP_URL_KEY': 'b3968d0207b54ece87cccc06515a89d4'


        })
        self.glance_mock = self.add_mock(glanceclient, 'Client')

        self.keystone_mock = self.add_mock(keystoneclient, 'Client')
        self.keystone_mock.return_value.auth_token = 'auth_token'

        self.provider = glance.GlanceImageProvider

    def test_get_image_info(self):

        r = FAKE_IMAGES_RESPONSE[0]
        self.glance_mock.return_value.images.get.return_value = r

        p = self.provider(self.config)
        hmac.new = mock.Mock(return_value=hmac.new('abc'))
        time.time = mock.Mock(return_value=42)

        info = p.get_image_info('foo')

        self.keystone_mock.assertCalledWith(
            username=self.config.KEYSTONE_USER,
            password=self.config.KEYSTONE_PASS,
            tenant_id=self.config.KEYSTONE_TENANT_ID,
            auth_url=self.config.KEYSTONE_AUTH_URL)

        self.glance_mock.assertCalledWith(
            self.config.GLANCE_VERSION,
            endpoint=self.config.GLANCE_URL,
            token='auth_token')

        self.glance_mock().images.get.assert_called_with('foo')

        self.assertEqual(info.serialize(), FAKE_IMAGE_INFO[0])

    def test_list_images(self):
        r = FAKE_IMAGES_RESPONSE
        self.glance_mock.return_value.images.list.return_value = r

        p = self.provider(self.config)

        info = p.list_images()

        self.keystone_mock.assertCalledWith(
            username=self.config.KEYSTONE_USER,
            password=self.config.KEYSTONE_PASS,
            tenant_id=self.config.KEYSTONE_TENANT_ID,
            auth_url=self.config.KEYSTONE_AUTH_URL)

        self.glance_mock.assertCalledWith(
            self.config.GLANCE_VERSION,
            endpoint=self.config.GLANCE_URL,
            token='auth_token')

        self.assertEqual([i.serialize() for i in info], FAKE_IMAGE_INFO)

    def test_get_image_none(self):

        e = glance_exceptions.HTTPNotFound
        self.glance_mock.return_value.images.get.side_effect = e

        p = self.provider(self.config)

        self.assertRaises(p.ImageDoesNotExist, p.get_image_info, 'foo')

    def test_list_image_none(self):

        self.glance_mock.return_value.images.list.return_value = []

        p = self.provider(self.config)
        info = p.list_images()

        self.assertEqual(info, [])

    def test_invalid_credentials(self):

        e = keystone_exceptions.ClientException
        self.keystone_mock.side_effect = e

        p = self.provider(self.config)

        self.assertRaises(p.ImageProviderException, p.get_image_info, 'foo')

    def test_get_image_info_error(self):

        e = glance_exceptions.BaseException
        self.glance_mock.return_value.images.get.side_effect = e

        p = self.provider(self.config)

        self.assertRaises(p.ImageProviderException, p.get_image_info, 'foo')

    def test_list_images_error(self):

        e = glance_exceptions.BaseException
        self.glance_mock.return_value.images.list.side_effect = e

        p = self.provider(self.config)

        self.assertRaises(p.ImageProviderException, p.list_images)
