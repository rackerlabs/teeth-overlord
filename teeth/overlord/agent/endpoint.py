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
from twisted.internet.protocol import ServerFactory
from twisted.internet import reactor, threads

from teeth.overlord import models, encoding, errors, rest
from teeth.overlord.agent.protocol import TeethAgentProtocol


class AgentEndpointHandler(TeethAgentProtocol):
    endpoint = None

    def __init__(self):
        TeethAgentProtocol.__init__(self, encoding.TeethJSONEncoder('public'))
        self.handlers['v1'] = {
            'handshake': self.handle_handshake,
        }
        self.connection = models.AgentConnection(id=uuid.uuid4())

    def connectionLost(self, reason):
        self.endpoint.unregister_agent_protocol(self.connection.id)
        for d in self.pending_command_deferreds.values():
            d.errback(errors.AgentConnectionLostError())

        threads.deferToThread(self.connection.delete)

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
