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
    """Base class for errors generated in teeth."""
    message = 'An error occurred'
    details = 'An unexpected error occurred. Please try back later.'
    status_code = 500

    def serialize(self, view):
        """Turn a TeethError into a dict."""
        return OrderedDict([
            ('type', self.__class__.__name__),
            ('code', self.status_code),
            ('message', self.message),
            ('details', self.details),
        ])


class ChassisAlreadyReservedError(TeethError):
    """
    Error which occurs when the scheduler recommends a chassis, but
    someone else reserves it first. This should generally be handled
    by requesting another chassis from the scheduler.
    """
    message = 'Chassis already reserved'

    def __init__(self, chassis):
        self.details = 'Chassis {chassis_id} is already reserved.'.format(chassis_id=str(chassis.id))


class InsufficientCapacityError(TeethError):
    """
    Error which occurs when not enough capacity is available to
    fulfill a request.
    """
    message = 'Insufficient capacity'
    details = 'There was not enough capacity available to fulfill your request. Please try back later.'


class AgentNotConnectedError(TeethError):
    """
    Error which occurs when an RPC call is attempted against a chassis
    for which no agent is connected.
    """
    message = 'Agent not connected'

    def __init__(self, chassis_id, primary_mac_address):
        self.details = ('No agent is connected for chassis {chassis_id} (mac adddress '
                        '{primary_mac_address}).').format(
            chassis_id=chassis_id,
            primary_mac_address=primary_mac_address
        )


class AgentConnectionLostError(TeethError):
    """
    Error which occurs when an agent's connection is lsot while an RPC
    call is in progress.
    """
    message = 'Agent connection lost'
    details = 'The agent\'s connection was lost while performing your request.'


class AgentExecutionError(TeethError):
    """
    Exception class which represents errors that occurred in the agent.
    """
    message = 'Error executing command'

    def __init__(self, details):
        self.details = details


class UnsupportedContentTypeError(TeethError):
    """
    Error which occurs when a user supplies an unsupported
    `Content-Type` (ie, anything other than `application/json`).
    """
    message = 'Unsupported Content-Type'
    status_code = 400

    def __init__(self, content_type):
        self.details = 'Content-Type "{content_type}" is not supported'.format(content_type=content_type)


class InvalidContentError(TeethError):
    """
    Error which occurs when a user supplies invalid content, either
    because that content cannot be parsed according to the advertised
    `Content-Type`, or due to a content validation error.
    """
    message = 'Invalid request body'
    status_code = 400

    def __init__(self, details):
        self.details = details


class RequestedObjectNotFoundError(TeethError):
    """
    Error which is returned when a requested object is not found.
    """
    message = 'Requested object not found'
    status_code = 404

    def __init__(self, cls, id):
        super(RequestedObjectNotFoundError, self).__init__(cls, id)
        self.details = '{type} with id {id} not found.'.format(type=cls.__name__, id=id)
