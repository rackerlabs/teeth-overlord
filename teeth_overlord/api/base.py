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

import json
from uuid import UUID

from structlog import get_logger
from werkzeug.routing import Map, Rule, BaseConverter, ValidationError
from werkzeug.wrappers import BaseRequest, BaseResponse
from werkzeug.exceptions import HTTPException
from werkzeug.http import parse_options_header

from teeth_overlord import errors


class UUIDConverter(BaseConverter):
    """
    Validate and transform UUIDs in urls.
    """

    def __init__(self, url_map):
        super(UUIDConverter, self).__init__(url_map)

    def to_python(self, value):
        """
        Transform a UUID string into a python UUID.
        """
        try:
            return UUID(value)
        except ValueError:
            raise ValidationError()

    def to_url(self, value):
        """
        Transform a python UUID into a string.
        """
        return str(value)


class APIBase(object):
    """
    Base class for implementing API components.
    """
    def __init__(self, config, encoder):
        self.config = config
        self.log = get_logger()
        self.encoder = encoder
        self.url_map = Map(converters={'uuid': UUIDConverter})
        self.add_routes()

    def __call__(self, environ, start_response):
        request = BaseRequest(environ)
        return self.dispatch_request(request)(environ, start_response)

    def add_routes(self):
        """
        Called during initialization. Override to map relative routes to methods.
        """
        pass

    def route(self, method, pattern, fn):
        """
        Route a relative path to a method.
        """
        self.url_map.add(Rule(pattern, methods=[method], endpoint=fn))

    def dispatch_request(self, request):
        """
        Given a Werkzeug request, generate a Response.
        """
        url_adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = url_adapter.match()
            return endpoint(request, **values)
        except errors.TeethError as e:
            self.log.error('error handling request', exception=e)
            return self.return_error(request, e)
        except HTTPException as e:
            return e
        except Exception as e:
            self.log.error('error handling request', exception=e)
            return self.return_error(request, errors.TeethError())

    def get_absolute_url(self, request, path):
        """
        Given a request and an absolute path, attempt to construct an
        absolute URL by examining the `Host` and `X-Forwarded-Proto`
        headers.
        """
        host = request.headers.get('host')
        proto = request.headers.get('x-forwarded-proto', default='http')
        return "{proto}://{host}{path}".format(proto=proto, host=host, path=path)

    def return_ok(self, request, result):
        """
        Return 200 and serialize the correspondig result.
        """
        body = self.encoder.encode(result)
        return BaseResponse(body, status=200, content_type='application/json')

    def return_created(self, request, path):
        """
        Return 201 and a Location generated from `path`.
        """
        response = BaseResponse(status=201, content_type='application/json')
        response.headers.set('Location', self.get_absolute_url(request, path))
        return response

    def return_error(self, request, e):
        """
        Transform a TeethError into the apprpriate response and return it.
        """
        body = self.encoder.encode(e)
        return BaseResponse(body, status=e.status_code, content_type='application/json')

    def parse_content(self, request):
        """
        Extract the content from the passed request, and attempt to
        parse it according to the specified `Content-Type`.

        Note: currently only `application/json` is supported.
        """
        content_type_header = request.headers.get('content-type', default='application/json')
        content_type = parse_options_header(content_type_header)[0]

        if content_type == 'application/json':
            try:
                return json.loads(request.get_data())
            except Exception as e:
                raise errors.InvalidContentError(e.message)
        else:
            raise errors.UnsupportedContentTypeError(content_type)
