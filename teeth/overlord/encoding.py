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

import simplejson as json


class Serializable(object):
    def serialize(self, view):
        raise NotImplementedError()


class SerializationViews(object):
    PUBLIC = 'PUBLIC'


class TeethJSONEncoder(json.JSONEncoder):
    def __init__(self, view, **kwargs):
        json.JSONEncoder.__init__(self, **kwargs)
        self.view = view

    def default(self, o):
        if isinstance(o, Serializable):
            return o.serialize(self.view)
        else:
            return json.JSONEncoder.default(self, o)
