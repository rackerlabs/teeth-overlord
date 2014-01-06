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
import os
from teeth_overlord import config


def get_config():
    """Try to load a configuration file."""
    conf = config.LazyConfig()
    conf.set_file(os.environ.get('TEETH_SETTINGS_FILE') or os.path.join(os.path.dirname(__file__), 'settings.json'))
    conf.setup()  # force config to eval
    return conf
