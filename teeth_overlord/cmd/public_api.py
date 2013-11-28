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

from werkzeug.serving import run_simple

from teeth_overlord.config import Config
from teeth_overlord.service import global_setup
from teeth_overlord.api.public import TeethPublicAPIServer

def run():
    config = Config()
    global_setup(config)
    api = TeethPublicAPIServer(config)
    run_simple(config.API_HOST, config.API_PORT, api)
