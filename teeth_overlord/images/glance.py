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
import glanceclient
from glanceclient import exc as glance_exceptions

from keystoneclient.apiclient import exceptions as keystone_exceptions
from keystoneclient.v2_0 import client as keystone_client

import hashlib
import hmac

from teeth_overlord.images import base

import time


class GlanceImageProvider(base.BaseImageProvider):
    """A static image provider useful in a dev environment."""

    # A map of possible values for Glance backend
    def __init__(self, config):
        super(GlanceImageProvider, self).__init__(config)
        self.backend_map = {}
        self.backend_map['swift'] = self._get_swift_temp_urls
        self.backend_map['glance'] = self._get_glance_urls

    def _get_auth_token(self):
        try:
            auth = keystone_client.Client(
                username=self.config.KEYSTONE_USER,
                password=self.config.KEYSTONE_PASS,
                tenant_id=self.config.KEYSTONE_TENANT_ID,
                auth_url=self.config.KEYSTONE_AUTH_URL)
            return auth.auth_token
        except keystone_exceptions.ClientException as e:
            raise self.ImageProviderException(
                'Cannot Initialize Keystone Client: {}'.format(str(e)))

    def _get_glance_client(self):
        auth_token = self._get_auth_token()
        try:
            return glanceclient.Client(self.config.GLANCE_VERSION,
                                       endpoint=self.config.GLANCE_URL,
                                       token=auth_token)
        except glance_exceptions.BaseException as e:
            raise self.ImageProviderException(
                'Cannot Initialize Glance Client: {}'.format(str(e)))

    def _get_swift_temp_urls(self, url):
        try:
            key = self.config.SWIFT_TEMP_URL_KEY.encode('ascii', 'ignore')
        except UnicodeDecodeError:
            raise ValueError('SWIFT_TEMP_URL_KEY must be an ascii key.')
        try:
            temp_url_duration = int(self.config.SWIFT_TEMP_URL_DURATION)
        except ValueError:
            raise ValueError('SWIFT_TEMP_URL_DURATION must be an integer.')
        method = self.config.SWIFT_TEMP_URL_METHOD
        if method not in ['GET', 'PUT']:
            raise ValueError('SWIFT_TEMP_URL_METHOD must be either GET or PUT')

        # Parse out filename from glance url
        try:
            object_name = url['file'].split('/')[3]
        except KeyError as e:
            raise self.ImageProviderException(
                'Image URL {} improperly formatted'.format(str(e))
            )

        template = '/v1/AUTH_{tenant}/{container}/{object_name}'
        url = template.format(tenant=self.config.KEYSTONE_TENANT_ID,
                              container=self.config.GLANCE_SWIFT_CONTAINER,
                              object_name=object_name).lstrip('/')

        expiration = int(time.time() + temp_url_duration)
        hmac_body = '\n'.join([method, str(expiration), url])
        sig = hmac.new(key, hmac_body, hashlib.sha1).hexdigest()
        host = self.config.SWIFT_URL.rstrip('/')
        return ['{host}/{url}?temp_url_sig={sig}&temp_url_expires={exp}'
                .format(host=host, url=url, sig=sig, exp=expiration)]

    def _get_glance_urls(self, image):
        """Warning: provides a protected URL.
        """
        host = self.config.GLANCE_URL
        path = image['file']
        return ['{}/{}'.format(host.rstrip('/'), path.lstrip('/'))]

    def _get_hashes(self, image):
        return {'md5': image.get('checksum', None)}

    def _make_image_info(self, image):
        # Decide which url function we should use, defaulting to glance.
        glance_backend = self.config.GLANCE_BACKEND or "glance"
        if glance_backend not in self.backend_map.keys():
            raise ValueError("GLANCE_BACKEND must be one of: {}".format(
                self.backend_map.keys()
            ))

        urls = self.backend_map[glance_backend](image)
        return base.ImageInfo(id=image['id'],
                              name=image['name'],
                              urls=urls,
                              hashes=self._get_hashes(image))

    def get_image_info(self, image_id):
        glance = self._get_glance_client()

        try:
            image = glance.images.get(image_id)
        except glance_exceptions.HTTPNotFound as e:
            raise self.ImageDoesNotExist(
                'Image with id {} does not exist'.format(image_id))
        except glance_exceptions.BaseException as e:
            raise self.ImageProviderException(
                'Cannot Get Image From Glance: {}'.format(str(e)))

        image_info = self._make_image_info(image)
        return image_info

    def list_images(self):
        glance = self._get_glance_client()

        try:
            images = [i for i in glance.images.list()]
        except glance_exceptions.BaseException as e:
            raise self.ImageProviderException(
                'Cannot List Images From Glance: {}'.format(str(e)))

        return [self._make_image_info(i) for i in images]
