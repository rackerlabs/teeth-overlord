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

from uuid import UUID
from collections import OrderedDict

from twisted.python.reflect import namedAny

from teeth_overlord.encoding import Serializable


class ImageInfo(Serializable):
    """
    Information about an image.
    """
    def __init__(self, **kwargs):
        self.id = UUID(kwargs['id'])
        self.name = kwargs['name']
        self.urls = kwargs['urls']
        self.hashes = kwargs['hashes']

    def serialize(self, view):
        """Turn an ImageInfo into a dict."""
        return OrderedDict([
            ('id', self.id),
            ('name', self.name),
            ('urls', self.urls),
            ('hashes', self.hashes),
        ])


class BaseImageProvider(object):
    """
    A provider of images. Basically an abstraction of a glance client.
    """

    def get_image_info(self, image_id):
        """
        Return, via a deferred, an ImageInfo instance with information about the
        requested image.
        """
        raise NotImplementedError()


def get_image_provider(provider_type, provider_config):
    """
    Instantiate an image provider of the specified type using the given
    config. The `provider_config` is simply a dict of keyword arguments
    to the image provider class.
    """
    cls = namedAny(provider_type)
    print cls
    return cls(**provider_config)
