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
from teeth_agent.protocol import RPCProtocol
from twisted.internet.protocol import ServerFactory
from twisted.internet import reactor, threads, defer

from teeth_overlord import models, encoding, rest


class AgentEndpointProtocol(RPCProtocol):
    def __init__(self, endpoint, address):
        RPCProtocol.__init__(self, encoding.TeethJSONEncoder('public'), address)
        self.connection = models.AgentConnection(id=uuid.uuid4())
        self.endpoint = endpoint
        self.handlers = {}
        self.handlers['v1'] = {
            'handshake': self.handle_handshake,
        }
        self.on('command', self._on_command)

    def connectionLost(self, reason):
        self.endpoint.unregister_agent_protocol(self.connection.id)
        threads.deferToThread(self.connection.delete)

    def _command_failed(self, failure, command):
        self._log.err(failure)
        self.send_error_response({'msg': failure.getErrorMessage()}, command)

    def _on_command(self, topic, command):
        if command.version not in self.handlers:
            command.protocol.fatal_error('unknown command version')
            return

        if command.method not in self.handlers[command.version]:
            command.protocol.fatal_error('unknown command method')
            return

        handler = self.handlers[command.version][command.method]
        d = defer.maybeDeferred(handler, **command.params)
        d.addCallback(self.send_response, command)
        d.addErrback(self._command_failed, command)

    def handle_handshake(self, id=None, version=None):
        self._log.msg('received handshake', primary_mac_address=id, agent_version=version)
        self.connection.primary_mac_address = id
        self.connection.agent_version = version
        self.connection.endpoint_rpc_host = self.endpoint.config.AGENT_ENDPOINT_RPC_HOST
        self.connection.endpoint_rpc_port = self.endpoint.config.AGENT_ENDPOINT_RPC_PORT
        self.endpoint.register_agent_protocol(self.connection.id, self)

        def _saved(result):
            return self.connection

        return threads.deferToThread(self.connection.save).addCallback(_saved)


class AgentEndpointProtocolFactory(ServerFactory):
    protocol = AgentEndpointProtocol

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def buildProtocol(self, address):
        protocol = AgentEndpointProtocol(self.endpoint, address)
        protocol.factory = self
        return protocol


class AgentEndpoint(rest.RESTServer):
    app = Klein()

    def __init__(self, config):
        rpc_port = config.AGENT_ENDPOINT_RPC_PORT
        rpc_host = config.AGENT_ENDPOINT_RPC_HOST
        rest.RESTServer.__init__(self, config, rpc_host, rpc_port)
        self.agent_protocols = {}

    def register_agent_protocol(self, connection_id, protocol):
        self.agent_protocols[str(connection_id)] = protocol

    def unregister_agent_protocol(self, connection_id):
        connection_id = str(connection_id)
        if connection_id in self.agent_protocols:
            del self.agent_protocols[connection_id]

    @app.route('/v1.0/agent_connections/<string:connection_id>/command')
    def send_agent_command(self, request, connection_id):
        if not connection_id in self.agent_protocols:
            request.setResponseCode(404)
            return

        def _response(result):
            return self.return_ok(request, result)

        content = json.loads(request.content.read())
        method = content['method']
        args = content.get('args', [])
        kwargs = content.get('kwargs', {})

        d = self.agent_protocols[connection_id].send_command(method, *args, **kwargs)
        return d.addCallback(_response)

    def startService(self):
        rest.RESTServer.startService(self)
        agent_port = self.config.AGENT_ENDPOINT_AGENT_PORT
        agent_host = self.config.AGENT_ENDPOINT_AGENT_HOST
        self.agent_listener = reactor.listenTCP(agent_port, AgentEndpointProtocolFactory(self), interface=agent_host)

    def stopService(self):
        return defer.DeferredList([self.agent_listener.stopListening(), rest.RESTServer.stopService(self)])
