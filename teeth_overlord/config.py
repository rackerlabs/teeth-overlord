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
import os


class ConfigValue(object):
    """Base class for a configuration value."""

    def __init__(self, value=None):
        self.set(value)

    def set(self, value):

        try:
            self._value = self.parse(value)
        except (ValueError, TypeError) as e:
            raise e

    def get(self):
        return self._value

    @classmethod
    def parse(cls, value):
        return value


class ListConfigValue(ConfigValue):
    """List configuration value."""

    @classmethod
    def parse(cls, value):
        if isinstance(value, basestring):
            return value.split(',')

        if isinstance(value, (tuple, list)):
            return value

        raise TypeError("'{}' must be a comma-separated string, list, or tuple.".format(value))


class StrConfigValue(ConfigValue):
    """String configuration value."""

    @classmethod
    def parse(cls, value):
        if isinstance(value, basestring):
            return value
        raise ValueError("'{}' must be an instance of basestring.".format(value))


class IntConfigValue(ConfigValue):
    """Integer configuration value."""

    @classmethod
    def parse(cls, value):
        return long(value)


class FloatConfigValue(ConfigValue):
    """Float configuration value."""

    @classmethod
    def parse(cls, value):
        return float(value)


class BoolConfigValue(ConfigValue):
    """Boolean configuration value."""

    _bool_map = {
        '1': True, '0': False,
        'true': True, 'false': False,
        'True': True, 'False': False,
        True: True, False: False
    }

    @classmethod
    def parse(cls, value):
        if value in cls._bool_map:
            return cls._bool_map[value]
        raise TypeError("'{}' must be one of {}.".format(value, ', '.join(cls._bool_map.keys())))


class ConfigSource(object):
    """Base configuration source class.

    Used for fetching configuration keys from external sources.
    """
    def __init__(self, conf):
        self.conf = conf

    def set(self, key):
        """Return a value for a given key"""
        raise NotImplementedError


class EnvSource(ConfigSource):

    def get(self, key):
        print 'GETTING {}'.format(key)
        return os.environ.get(key, None)


class Config(object):

    _type_map = {
        list: ListConfigValue,
        int: IntConfigValue,
        float: FloatConfigValue,
        str: StrConfigValue,
        unicode: StrConfigValue,
        bool: BoolConfigValue
    }

    _loaded_files = []
    _config_files = []
    _loaded_sources = []
    _config_sources = []

    _config = {}

    def __init__(self, **kwargs):

        # set any initial values passed in via kwargs
        for k,v in kwargs:
            self.set(k, v)

        # take a stab at finding/loading a default configuration file if we aren't provided one
        if not self._config_files:
            self._config_files.append(os.path.join(os.path.dirname(__file__), 'settings.json'))

        self._load_files()
        self._run_sources()

    def _load_files(self):
        for f in list(self._config_files):
            if f not in self._loaded_files:
                for k,v in json.loads(open(f, 'r').read()).iteritems():
                    self.set(k,v)
                self._loaded_files.append(f)

        # we recurse a little bit if we happen to add some more unloaded files to CONFIG_FILES
        if set(self._config_files) - set(self._loaded_files):
            self._load_files()

    def _get_source(self, name):
        split = name.split('.')
        module = split[:-1]
        cls = split[-1]
        return getattr(__import__('.'.join(module), fromlist=[cls]), cls)

    def _run_sources(self):
        for s in self._config_sources:
            if s not in self._loaded_sources:
                source = self._get_source(s)(self)

                for k in ['CONFIG_FILES']:
                    val = source.get(k)
                    if val is not None:
                        print 'setting value {}:{} from source {}'.format(k, val, source.__class__)
                        self.set(k, val)
                        self._load_files()

                for k,v in self._config.iteritems():
                    val = source.get(k)
                    if val is not None:
                        print 'setting value {}:{} from source {}'.format(k, val, source.__class__)
                        self.set(k, val)

                self._loaded_sources.append(s)


    def get(self, name, required=True):
        if name in self._config:
            return self._config.get(name).get()

        if required:
            raise ValueError('Config does not contain key {}'.format(name))

        return None

    def set(self, name, value):

        print 'SETTING {}:{}'.format(name, value)

        if name == 'CONFIG_FILES':
            # special config values that let us know where to look for more config files
            self._config_files = self._config_files + ListConfigValue(value).get()
            return
        elif name == 'CONFIG_SOURCES':
            # special config values that let us know where to look for more config sources
            self._config_sources = self._config_sources + ListConfigValue(value).get()
            return
        else:
            for k,v in self._type_map.iteritems():
                if isinstance(value, k):
                    self._config[name] = v(value)
                    return

        raise ValueError("Cannot set key '{}' to value '{}', unknown type '{}'".format(name, value, type(value)))
