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
import uuid

from klein import Klein
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory
from twisted.internet.defer import maybeDeferred
from twisted.internet import reactor, defer, threads

from teeth.overlord import models, encoding, errors, rest


DEFAULT_PROTOCOL_VERSION = 'v1'


class AgentEndpointHandler(LineReceiver):
    encoder = encoding.TeethJSONEncoder('public')
    endpoint = None

    def __init__(self):
        self.handlers = {}
        self.handlers['v1'] = {
            'handshake': self.handle_handshake,
        }
        self.connection = models.AgentConnection(id=uuid.uuid4())
        self.pending_command_deferreds = {}

    def lineReceived(self, line):
        line = line.strip()
        if not line:
            return

        message = json.loads(line)
        if 'method' in message:
            self.handle_command(message)
        elif 'result' in message:
            self.handle_response(message)

    def connectionLost(self, reason):
        self.endpoint.unregister_agent_protocol(self.connection.id)
        for d in self.pending_command_deferreds.values():
            d.errback(errors.AgentConnectionLostError())

        threads.deferToThread(self.connection.delete)

    def send_command(self, command):
        message_id = str(uuid.uuid4())
        d = defer.Deferred()
        self.pending_command_deferreds[message_id] = d
        self.sendLine(self.encoder.encode({
            'id': message_id,
            'version': DEFAULT_PROTOCOL_VERSION,
            'method': command['method'],
            'args': command.get('args', []),
            'kwargs': command.get('kwargs', {}),
        }))
        return d

    def handle_command(self, message):
        message_id = message['id']
        version = message['version']
        args = message.get('args', [])
        kwargs = message.get('kwargs', {})
        d = maybeDeferred(self.handlers[version][message['method']], *args, **kwargs)
        d.addCallback(self.send_response, version, message_id)

    def send_response(self, result, version, message_id):
        self.sendLine(self.encoder.encode({
            'id': message_id,
            'version': version,
            'result': result,
        }))

    def handle_response(self, message):
        d = self.pending_command_deferreds.pop(message['id'])
        error = message.get('error', None)
        if error:
            d.errback(error)
        else:
            d.callback(message.get('result', None))

    def handle_handshake(self, primary_mac_address, agent_version):
        self.connection.primary_mac_address = primary_mac_address
        self.connection.agent_version = agent_version
        self.connection.endpoint_rpc_host = self.endpoint.config.AGENT_ENDPOINT_RPC_HOST
        self.connection.endpoint_rpc_port = self.endpoint.config.AGENT_ENDPOINT_RPC_PORT
        self.endpoint.register_agent_protocol(self.connection.id, self)

        def _saved(result):
            return self.connection

        return threads.deferToThread(self.connection.save).addCallback(_saved)


class AgentEndpointHandlerFactory(ServerFactory):
    protocol = AgentEndpointHandler

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def buildProtocol(self, address):
        protocol = ServerFactory.buildProtocol(self, address)
        protocol.endpoint = self.endpoint
        return protocol


class AgentEndpoint(rest.RESTServer):
    app = Klein()

    def __init__(self, config):
        rpc_port = config.AGENT_ENDPOINT_RPC_PORT
        rpc_host = config.AGENT_ENDPOINT_RPC_HOST
        super(AgentEndpoint, self).__init__(config, rpc_host, rpc_port)
        self.agent_protocols = {}

    def register_agent_protocol(self, connection_id, protocol):
        print "Registered agent connection {}".format(str(connection_id))
        self.agent_protocols[str(connection_id)] = protocol

    def unregister_agent_protocol(self, connection_id):
        del self.agent_protocols[str(connection_id)]

    @app.route('/v1.0/agent_connections/<string:connection_id>/command')
    def send_agent_command(self, request, connection_id):
        if not connection_id in self.agent_protocols:
            request.setResponseCode(404)
            return

        def _response(result):
            return self.return_ok(result)

        d = self.agent_protocols[connection_id].send_command(json.loads(request.content.read()))
        return d.addCallback(_response)

    def listen(self):
        agent_port = self.config.AGENT_ENDPOINT_AGENT_PORT
        agent_host = self.config.AGENT_ENDPOINT_AGENT_HOST
        reactor.listenTCP(agent_port, AgentEndpointHandlerFactory(self), interface=agent_host)
        super(AgentEndpoint, self).listen()
