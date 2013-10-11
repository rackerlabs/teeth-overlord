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
from structlog import get_logger
from teeth_agent.protocol import RPCProtocol, require_parameters
from twisted.internet.protocol import ServerFactory
from twisted.internet import reactor, threads, defer

from teeth_overlord import models, encoding, rest, errors


class AgentEndpointProtocol(RPCProtocol):
    """
    Wrapper around the agent's RPCProtocol which provides
    method implementations specific to the endpoint.
    """
    def __init__(self, endpoint, address):
        RPCProtocol.__init__(self, encoding.TeethJSONEncoder('public'), address)
        self.connection = None
        self.agent_logger = get_logger()
        self.endpoint = endpoint
        self.handlers = {}
        self.handlers['v1'] = {
            'handshake': self.handle_handshake,
            'ping': self.handle_ping,
            'log': self.handle_log,
        }
        self.on('command', self._on_command)

    def connectionLost(self, reason):
        """
        The connection was lost, remove this connection from the local
        registry and delete it from the database.
        """
        self._log.msg('connection lost')
        if self.connection:
            self.endpoint.unregister_agent_protocol(self.connection.id)
            threads.deferToThread(self.connection.delete)

    def _command_failed(self, failure, command):
        """
        Inform an agent that a comand failed. Log the error and return
        it to the agent.
        """
        self._log.err(failure)

        if hasattr(failure.value, 'fatal') and failure.value.fatal:
            command.protocol.fatal_error(failure.getErrorMessage())
        else:
            self.send_error_response({'msg': failure.getErrorMessage()}, command)

    def _on_command(self, topic, command):
        """
        Map an agent command to the appropriate local method, call that
        method, and register callbacks for the results.
        """
        if command.version not in self.handlers:
            command.protocol.fatal_error('unknown command version')
            return

        if command.method not in self.handlers[command.version]:
            command.protocol.fatal_error('unknown command method')
            return

        handler = self.handlers[command.version][command.method]
        d = defer.maybeDeferred(handler, command)
        d.addCallback(self.send_response, command)
        d.addErrback(self._command_failed, command)

    @require_parameters('id', 'version', fatal=True)
    def handle_handshake(self, command):
        """
        Handle a handshake from the agent. The agent will pass in its
        primary MAC address as its ID (so that we can map the agent to
        the appropriate Chassis), as well as its version.

        Eventually we will probably want to do a rolling rebuild of
        any chassis running an old version of the agent.
        """
        id = command.params['id']
        version = command.params['version']
        self._log.msg('received handshake', primary_mac_address=id, agent_version=version)
        self.connection = models.AgentConnection(id=uuid.uuid4())
        self.connection.primary_mac_address = id
        self.connection.agent_version = version
        self.connection.endpoint_rpc_host = self.endpoint.config.AGENT_ENDPOINT_RPC_HOST
        self.connection.endpoint_rpc_port = self.endpoint.config.AGENT_ENDPOINT_RPC_PORT
        self.endpoint.register_agent_protocol(self.connection.id, self)
        self.agent_logger = self.agent_logger.bind(connection_id=self.connection.id,
                                                   primary_mac_address=id,
                                                   agent_version=version)

        def _saved(result):
            return self.connection

        return threads.deferToThread(self.connection.save).addCallback(_saved)

    def handle_ping(self, command):
        """
        Handle a ping from the agent.
        """
        return command.params

    @require_parameters('message', 'time')
    def handle_log(self, command):
        """
        Handle log messages from the agent.

        TODO: put these in the database? Or just treat them as a normal
              log message?
        """
        self.agent_logger.msg(**command.params)


class AgentEndpointProtocolFactory(ServerFactory):
    """
    ServerFactory for AgentEndpointProtocols. Each created protocol
    will be passed an AgentEndpoint instance, which it will use for
    certain operations that modify local state.
    """
    protocol = AgentEndpointProtocol

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def buildProtocol(self, address):
        """
        Make a new AgentEndpointProtocol.
        """
        protocol = AgentEndpointProtocol(self.endpoint, address)
        protocol.factory = self
        return protocol


class AgentEndpoint(rest.RESTServer):
    """
    AgentEndpoint service. Exposes a REST API for interacting with
    connected agents, as well as agent RPC protocol endpoint that
    agents connect to.
    """
    app = Klein()

    def __init__(self, config):
        rpc_port = config.AGENT_ENDPOINT_RPC_PORT
        rpc_host = config.AGENT_ENDPOINT_RPC_HOST
        rest.RESTServer.__init__(self, config, rpc_host, rpc_port)
        self.agent_protocols = {}

    def register_agent_protocol(self, connection_id, protocol):
        """
        Register an agent protocol so that it can be interacted with.
        """
        self.agent_protocols[str(connection_id)] = protocol

    def unregister_agent_protocol(self, connection_id):
        """
        Unregister an agent protocol, usually after a disconnect.
        """
        connection_id = str(connection_id)
        if connection_id in self.agent_protocols:
            del self.agent_protocols[connection_id]

    @app.route('/v1.0/agent_connections/<string:connection_id>/command')
    def send_agent_command(self, request, connection_id):
        """
        Send a command to an agent based on its connection ID.
        """
        if not connection_id in self.agent_protocols:
            request.setResponseCode(404)
            return

        def _on_success(response):
            return self.return_ok(request, {'result': response.result})

        def _on_failure(response):
            return self.return_error(request, errors.AgentExecutionError(response.error))

        content = json.loads(request.content.read())
        method = content['method']
        params = content.get('params', {})

        d = self.agent_protocols[connection_id].send_command(method, params)
        d.addCallbacks(_on_success, _on_failure)
        return d

    def startService(self):
        """
        Start the AgentEndpoint.
        """
        rest.RESTServer.startService(self)
        agent_port = self.config.AGENT_ENDPOINT_AGENT_PORT
        agent_host = self.config.AGENT_ENDPOINT_AGENT_HOST
        factory = AgentEndpointProtocolFactory(self)
        self.agent_listener = reactor.listenTCP(agent_port, factory, interface=agent_host)

    def stopService(self):
        """
        Stop the AgentEndpoint.
        """
        return defer.DeferredList([
            self.agent_listener.stopListening(),
            rest.RESTServer.stopService(self)
        ])
