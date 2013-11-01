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

from twisted.internet import defer

from teeth_overlord.images.base import BaseImageProvider, ImageInfo
from teeth_overlord.errors import ImageNotFoundError


class StaticImageProvider(BaseImageProvider):
    """
    A static image provider useful in a dev environment.
    """

    def __init__(self, images=[]):
        self.images = {image.id: ImageInfo(image) for image in images}

    def get_image_info(self, image_id):
        """
        Return, via a deferred, an ImageInfo instance with information about the
        requested image.
        """
        image_id = str(image_id)

        if image_id not in self.image_infos:
            defer.fail(ImageNotFoundError(image_id))

        defer.succeed(self.image_infos[image_id])
