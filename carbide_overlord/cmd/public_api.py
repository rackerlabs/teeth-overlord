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

from carbide_overlord.api import public
from carbide_overlord import config as carbide_config
from carbide_overlord import service


def run():
    config = carbide_config.get_config()
    service.global_setup(config)
    api = public.CarbidePublicAPIServer(config)
    listen_address = (config.PUBLIC_API_HOST, config.PUBLIC_API_PORT)
    server = wsgiserver.CherryPyWSGIServer(listen_address, api)
    try:  # ^C doesn't work without this try/except
        server.start()
    except KeyboardInterrupt:
        server.stop()
