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

import abc
from collections import OrderedDict

from stevedore import driver

from teeth_rest.encoding import Serializable


class ImageInfo(Serializable):
    """
    Information about an image.
    """
    def __init__(self, **kwargs):
        self.id = kwargs['id']
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

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_image_info(self, image_id):
        """
        Returns an ImageInfo instance with information about the requested
        image.
        """


def get_image_provider(provider_name, config):
    mgr = driver.DriverManager(
        namespace='teeth_overlord.image.providers',
        name=provider_name,
        invoke_on_load=True,
        invoke_kwds=config,
    )
    return mgr.driver
