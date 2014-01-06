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
import threading


class ConfigException(Exception):
    pass


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


class Config(object):
    """This class exists to give some type safety to a configuration instance and allow some magic
    coersion of values that come from un-typed sources (environment variables, etc).

    Instantiate this with a dict and any attempts to overwrite a key with an incompatable type will
    throw.

    See each *Value implementation for details, coersion, etc.
    """

    _type_map = {
        list: ListConfigValue,
        int: IntConfigValue,
        float: FloatConfigValue,
        str: StrConfigValue,
        unicode: StrConfigValue,
        bool: BoolConfigValue
    }

    def __init__(self, **kwargs):

        self._config = {}

        for k,v in kwargs.items():
            self.set(k, v)

    def get(self, name, required=True):
        if name in self._config:
            return self._config.get(name).get()

        if required:
            raise ValueError('Config does not contain key {}'.format(name))

        return None

    def set(self, name, value):

        if name in self._config:
            # we rely on ConfigValue to validate this
            self._config[name].set(value)
            return self.get(name)

        for k,v in self._type_map.iteritems():
            if isinstance(value, k):
                # we rely on ConfigValue to validate this
                self._config[name] = v(value)
                return self.get(name)

        raise ValueError("Cannot set key '{}' to value '{}', unknown type '{}'".format(name, value, type(value)))

    def items(self):
        for k,v in self._config.items():
            yield k, v.get()


class LazyConfig(object):

    def __init__(self):

        self._config = None
        self._user_config = None
        self._config_file = None

        self._setup_lock = threading.Lock()

        self._callbacks = []

    def __getattr__(self, name):
        if name.isupper():
            if not self._config:
                self._setup()
            return self._config.get(name)
        else:
            return object.__getattribute__(self, name)

    def _setup(self, user_config=None):
        # We want to be sure we only ever setup a config once per instance.
        self._setup_lock.acquire()
        if not self._config:
            try:
                # If we are given a config directly with set_config(), use that.
                if self._user_config:
                    config = self._user_config
                # Otherwise, try to load a config file.
                elif self._config_file:
                    try:
                        config = json.loads(open(self._config_file, 'r').read())
                    except IOError as e:
                        raise ConfigException("Cannot read settings file: {}".format(str(e)))
                    except ValueError as e:
                        raise ConfigException("Cannot parse settings file: {}".format(str(e)))
                else:
                    raise ConfigException("Must call set_config() or set_file().")

                self._config = Config(**config)

                self._run_sources()
                self._run_callbacks()
            finally:
                self._setup_lock.release()

    def _load_module(self, name):
        module = name.split('.')
        cls = module.pop()
        return getattr(__import__('.'.join(module), fromlist=[str(cls)]), cls)

    def _run_callbacks(self):
        for cb in self._callbacks:
            cb(self)
        self._callbacks = set()

    def _run_sources(self):
        # run any sources specified in the config file
        sources = self._config.get('CONFIG_SOURCES', False) or []
        for source in sources:
            module = source[0]
            args = source[1:]
            instance = self._load_module(module)(self, *args)
            for k,v in self._config.items():
                val = instance.get(k)
                if val is not None:
                    self._config.set(k, val)

    def set_config(self, user_config):
        """Set the configuration to a given dict, do not load a settings file."""
        self._user_config = user_config

    def set_file(self, f):
        """Load settings from a JSON file at the given path."""
        self._config_file = f

    def add_callback(self, cb):
        """Call the given object after config setup, guaranteed to only call once."""
        self._callbacks.append(cb)


settings = LazyConfig()
