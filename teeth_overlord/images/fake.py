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

from teeth_overlord.images.base import BaseImageProvider, ImageInfo

FAKE_IMAGE_INFO = {
    'name': 'Default Example Image',
    'urls': ['http://example.org/images/8226c769-3739-4ee6-921c-82110da6c669.raw'],
    'hashes': {
        'md5': 'c2e5db72bd7fd153f53ede5da5a06de3',
    },
}


class FakeImageProvider(BaseImageProvider):
    """
    A static image provider useful in a dev environment.
    """

    def get_image_info(self, image_id):
        """
        Returns an ImageInfo instance with information about the requested
        image.
        """
        return ImageInfo(**dict(FAKE_IMAGE_INFO.items() + [('id', image_id)]))
