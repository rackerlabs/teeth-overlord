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
    """
    Base class for things that can be serialized in Teeth Overlord.
    """
    def serialize(self, view):
        """
        Turn this object into a dict.
        """
        raise NotImplementedError()


class SerializationViews(object):
    """
    The set of available serialization 'views'. Views represent the
    context in which an object is being serialized. For example, an
    object might be serialized differently for a PUBLIC view as compared
    to an ADMIN view.

    Currently unused. We may want to replace this with some sort of
    more flexible capabilities mechanism.
    """
    PUBLIC = 'PUBLIC'


class TeethJSONEncoder(json.JSONEncoder):
    """
    A slightly customized JSON encoder. This does two things beyond
    what the default can do:

    1. Knows about views
    2. Appends a newline to responses when configured to pretty-print,
       in order to make use of curl less painful from most shells.
    """
    def __init__(self, view, **kwargs):
        json.JSONEncoder.__init__(self, **kwargs)
        self.view = view

    def encode(self, o):
        """
        Turn an object into JSON.
        """
        delimiter = ''

        # Note: if indent is None, newlines are still inserted, so we should too
        if self.indent is not None:
            delimiter = '\n'

        return super(TeethJSONEncoder, self).encode(o) + delimiter

    def default(self, o):
        """
        Turn an object into a serializable object. In particular, by
        calling :meth:`.Serializable.serialize`.
        """
        if isinstance(o, Serializable):
            return o.serialize(self.view)
        else:
            return json.JSONEncoder.default(self, o)
