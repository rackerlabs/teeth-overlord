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

from collections import OrderedDict

from teeth_overlord.models import Serializable


class TeethError(Exception, Serializable):
    message = 'An error occurred'
    details = 'An unexpected error occurred. Please try back later.'
    status_code = 500

    def serialize(self, view):
        return OrderedDict([
            ('type', self.__class__.__name__),
            ('code', self.status_code),
            ('message', self.message),
            ('details', self.details),
        ])


class InsufficientCapacityError(TeethError):
    message = 'Insufficient capacity'
    details = 'There was not enough capacity available to fulfill your request. Please try back later.'


class AgentNotConnectedError(TeethError):
    message = 'Agent not connected'

    def __init__(self, chassis_id, primary_mac_address):
        self.details = 'No agent is connected for chassis {chassis_id} (mac adddress {primary_mac_address}).'.format(
            chassis_id=chassis_id,
            primary_mac_address=primary_mac_address
        )


class AgentConnectionLostError(TeethError):
    message = 'Agent connection lost'
    details = 'The agent\'s connection was lost while performing your request.'


class UnsupportedContentTypeError(TeethError):
    message = 'Unsupported Content-Type'
    status_code = 400

    def __init__(self, content_type):
        self.details = 'Content-Type "{content_type}" is not supported'.format(content_type=content_type)


class InvalidContentError(TeethError):
    message = 'Invalid request body'
    status_code = 400

    def __init__(self, error):
        self.details = error.message
