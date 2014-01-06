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

from cherrypy import wsgiserver

from teeth_overlord.api import public
from teeth_overlord import service
from teeth_overlord import settings


def run():
    config = settings.get_config()
    service.global_setup(config)
    api = public.TeethPublicAPIServer(config)
    listen_address = (config.API_HOST, config.API_PORT)
    server = wsgiserver.CherryPyWSGIServer(listen_address, api)
    try:  # ^C doesn't work without this try/except
        server.start()
    except KeyboardInterrupt:
        server.stop()
