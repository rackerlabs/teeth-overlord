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
from keystoneclient.v2_0 import client as keystone_client

from teeth_overlord.images import base


class GlanceImageInfo(base.ImageInfo):
    """Information about an image hosted in Glance."""
    def __init__(self, **kwargs):
        self.extra_headers = kwargs.pop('extra_headers', {})
        super(GlanceImageInfo, self).__init__(**kwargs)

    def serialize(self):
        """Turn a GlanceImageInfo into a dict."""
        return collections.OrderedDict([
            ('id', self.id),
            ('name', self.name),
            ('urls', self.urls),
            ('hashes', self.hashes),
            ('extra_headers', self.extra_headers)
        ])


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

    def _get_glance_client(self, auth_token):
        try:
            return glanceclient.Client(self.config.GLANCE_VERSION,
                                       endpoint=self.config.GLANCE_URL,
                                       token=auth_token)
        except glance_exceptions.BaseException as e:
            raise self.ImageProviderException(
                'Cannot Initialize Glance Client: {}'.format(str(e)))

    def _get_urls(self, image):
        host = self.config.GLANCE_URL
        path = image['file']
        return ['{}/{}'.format(host.rstrip('/'), path.lstrip('/'))]

    def _get_hashes(self, image):
        return {'md5': image['checksum']}

    def _make_image_info(self, image, auth_token):
        extra_headers = {
            'X-Keystone-Token': auth_token
        }
        return GlanceImageInfo(id=image['id'],
                               name=image['name'],
                               urls=self._get_urls(image),
                               hashes=self._get_hashes(image),
                               extra_headers=extra_headers)

    def get_image_info(self, image_id):
        auth_token = self._get_auth_token()
        glance = self._get_glance_client(auth_token)

        try:
            image = glance.images.get(image_id)
        except glance_exceptions.HTTPNotFound as e:
            raise self.ImageDoesNotExist(
                'Image with id {} does not exist'.format(image_id))
        except glance_exceptions.BaseException as e:
            raise self.ImageProviderException(
                'Cannot Get Image From Glance: {}'.format(str(e)))

        image_info = self._make_image_info(image, auth_token)
        return image_info

    def list_images(self):
        auth_token = self._get_auth_token()
        glance = self._get_glance_client(auth_token)

        try:
            images = [i for i in glance.images.list()]
        except glance_exceptions.BaseException as e:
            raise self.ImageProviderException(
                'Cannot List Images From Glance: {}'.format(str(e)))

        return [self._make_image_info(i, auth_token) for i in images]
