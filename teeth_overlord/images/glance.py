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

from teeth_overlord.images import base


class GlanceImageProvider(base.BaseImageProvider):
    """A static image provider useful in a dev environment."""

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
        try:
            return glanceclient.Client(self.config.GLANCE_VERSION,
                                       endpoint=self.config.GLANCE_URL,
                                       token=self._get_auth_token())
        except glance_exceptions.BaseException as e:
            raise self.ImageProviderException(
                'Cannot Initialize Glance Client: {}'.format(str(e)))

    def _get_urls(self, image):
        host = self.config.GLANCE_URL
        path = image['file']
        return ['{}/{}'.format(host.rstrip('/'), path.lstrip('/'))]

    def _get_hashes(self, image):
        return {'md5': image['checksum']}

    def _make_image_info(self, image):
        return base.ImageInfo(id=image['id'],
                              name=image['name'],
                              urls=self._get_urls(image),
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

        return self._make_image_info(image)

    def list_images(self):
        glance = self._get_glance_client()

        try:
            images = [i for i in glance.images.list()]
        except glance_exceptions.BaseException as e:
            raise self.ImageProviderException(
                'Cannot List Images From Glance: {}'.format(str(e)))

        return [self._make_image_info(i) for i in images]
