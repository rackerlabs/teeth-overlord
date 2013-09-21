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
from structlog import get_logger
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.python.failure import Failure
from werkzeug.http import parse_options_header

from teeth_overlord import errors, encoding, service


class RESTServer(service.TeethService):
    def __init__(self, config, host, port, view=encoding.SerializationViews.PUBLIC, indent=4):
        self.config = config
        self.encoder = encoding.TeethJSONEncoder(view, indent=indent)
        self.listen_host = host
        self.listen_port = port
        self.log = get_logger(port=port, host=host)

    def get_absolute_url(self, request, path):
        host = request.getHeader('host')
        proto = request.getHeader('x-forwarded-proto') or 'http'
        return "{proto}://{host}{path}".format(proto=proto, host=host, path=path)

    def return_error(self, error, request):
        self.log.err(error)

        if isinstance(error, Failure):
            error = error.value

        if isinstance(error, errors.TeethError):
            request.setResponseCode(error.status_code)
            request.setHeader('Content-Type', 'application/json')
            return self.encoder.encode(error)
        else:
            request.setResponseCode(500)
            request.setHeader('Content-Type', 'application/json')
            return self.encoder.encode(errors.TeethError())

    def return_ok(self, request, result):
        request.setResponseCode(200)
        request.setHeader('Content-Type', 'application/json')
        return self.encoder.encode(result)

    def parse_content(self, request):
        content_type = request.getHeader('content-type')
        if content_type:
            content_type = parse_options_header(content_type)[0]
            if content_type != 'application/json':
                raise errors.UnsupportedContentTypeError(content_type)

        try:
            return json.loads(request.content.read())
        except Exception as e:
            raise errors.InvalidContentError(e)

    def startService(self):
        service.TeethService.startService(self)
        self.listener = reactor.listenTCP(self.listen_port, Site(self.app.resource()), interface=self.listen_host)

    def stopService(self):
        return self.listener.stopListening()
