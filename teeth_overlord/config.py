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

import collections
import etcd
import json
import os
import threading


class ConfigException(Exception):
    pass


class ConfigSource(object):
    """Base configuration source class.

    Used for fetching configuration keys from external sources.
    """
    def __init__(self, conf, *args):
        self._conf = conf

    def get(self, key):
        """Return a value for a given key."""
        raise NotImplementedError


class EnvSource(ConfigSource):
    """Replaces settings with values from os.environ."""

    def get(self, key):
        return os.environ.get(key, None)


class EtcdSource(ConfigSource):
    """Replaces settings with values from etcd."""

    def __init__(self, conf, host_key, port_key, dir_key):
        super(EtcdSource, self).__init__(conf)
        self._host = self._conf[host_key]
        self._port = self._conf[port_key]
        self._dir = self._conf[dir_key]
        self._client = etcd.Client(host=self._host, port=self._port)

    def _mkpath(self, key):
        return "{}/{}".format(self._dir, key)

    def get(self, key):
        try:
            return self._client.get(self._mkpath(key)).value
        except KeyError:
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
            value = value.split(',')

        if isinstance(value, (tuple, list)):
            return value

        raise ValueError(("'{}' must be a comma-separated string, ") +
                         ("list, or tuple.").format(value))


class StrConfigValue(ConfigValue):
    """String configuration value."""

    @classmethod
    def parse(cls, value):
        if isinstance(value, basestring):
            return value
        raise ValueError("'{}' must be an instance of basestring."
                         .format(value))


class IntConfigValue(ConfigValue):
    """Integer configuration value."""

    @classmethod
    def parse(cls, value):
        return int(value)


class FloatConfigValue(ConfigValue):
    """Float configuration value."""

    @classmethod
    def parse(cls, value):
        return float(value)


class BoolConfigValue(ConfigValue):
    """Boolean configuration value."""

    _bool_map = {
        '1': True, '0': False,
        1: True, 0: False,
        'true': True, 'false': False,
        'True': True, 'False': False,
        True: True, False: False
    }

    @classmethod
    def parse(cls, value):
        if value in cls._bool_map:
            return cls._bool_map[value]
        keys = ', '.join([str(v) for v in cls._bool_map.keys()])
        raise ValueError("'{}' must be one of {}.".format(value, keys))


class Config(object):
    """This class exists to give some type safety to a configuration
    instance and allow some magic coersion of values that come from
    un-typed sources (environment variables, etc).

    Instantiate this with a dict and any attempts to overwrite a key
    with an incompatable type will throw.

    See each *Value implementation for details, coersion, etc.
    """

    # order matters, because isinstance(True, int) == True
    _type_map = collections.OrderedDict([
        (bool, BoolConfigValue),
        (list, ListConfigValue),
        (int, IntConfigValue),
        (float, FloatConfigValue),
        (str, StrConfigValue),
        (unicode, StrConfigValue)
    ])

    def __init__(self, **kwargs):

        self._config = {}

        for k, v in kwargs.items():
            self.set(k, v)

    def __getattr__(self, name):
        if name.isupper():
            return self.get(name)
        else:
            return object.__getattribute__(self, name)

    def __getitem__(self, name):
        if name.isupper():
            return self.get(name)
        else:
            # throw
            return self[name]

    def __setitem__(self, name, value):
        if name.isupper():
            return self.set(name, value)
        else:
            # throw
            self[name] = value

    def __setattr__(self, name, value):
        if name.isupper():
            self.set(name, value)
        else:
            return object.__setattr__(self, name, value)

    def get(self, name, required=True):
        if name in self._config:
            return self._config.get(name).get()

        if required:
            raise ValueError('Config does not contain key {}'
                             .format(name))

        return None

    def set(self, name, value):

        if name in self._config:
            # we rely on ConfigValue to validate this
            self._config[name].set(value)
            return self.get(name)

        for k, v in self._type_map.iteritems():
            if isinstance(value, k):
                # we rely on ConfigValue to validate this
                self._config[name.upper()] = v(value)
                return self.get(name)

        raise ValueError(("Cannot set key '{}' to value '{}', ") +
                         ("unknown type '{}'")
                         .format(name, value, type(value)))

    def items(self):
        for k, v in self._config.items():
            yield k, v.get()


class LazyConfig(object):

    def __init__(self, config_file=None, config=None):

        self._config = None
        self._user_config = config
        self._config_file = config_file

        self._setup_lock = threading.Lock()

        self._sources = []
        self._callbacks = []

    def __getattr__(self, name):
        if name.isupper():
            if not self._config:
                self._setup()
            return self._config.get(name)
        else:
            return object.__getattribute__(self, name)

    def __getitem__(self, name):
        if name.isupper():
            if not self._config:
                self._setup()
            return self._config.get(name)
        else:
            # throw
            return self[name]

    def _setup(self):
        self._setup_lock.acquire()
        try:
            if not self._config:
                # If we are given a config directly with
                # set_config(), use that.
                if self._user_config:
                    config = self._user_config
                # Otherwise, try to load a config file.
                elif self._config_file:
                    try:
                        config = json.loads(
                            open(self._config_file, 'r').read())
                    except IOError as e:
                        raise ConfigException(
                            "Cannot read settings file: {}"
                            .format(str(e)))
                    except ValueError as e:
                        raise ConfigException(
                            "Cannot parse settings file: {}"
                            .format(str(e)))
                else:
                    raise ConfigException(
                        "Must call set_config() or set_file().")

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

    def _run_sources(self):
        # run any sources specified in the config file
        sources = (self._config.get('CONFIG_SOURCES', False) or [])
        sources = sources + self._sources
        for source in sources:
            module = source[0]
            args = source[1:]
            instance = self._load_module(module)(self, *args)
            for k, v in self._config.items():
                val = instance.get(k)
                if val is not None:
                    self._config.set(k, val)

    def setup(self):
        """Force configuration evaluation."""
        if self._config:
            raise ConfigException("Configuration already set up.")
        self._setup()

    def add_source(self, s):
        """Add a configuration source."""
        self._sources.append(s)

    def add_callback(self, cb):
        """Call the given object after config setup."""
        self._callbacks.append(cb)


def get_config():
    """Try to load a configuration file."""
    f = os.environ.get('TEETH_SETTINGS_FILE')
    f = f or os.path.join(os.path.dirname(__file__), 'settings.json')
    conf = LazyConfig(config_file=f)
    conf.setup()  # force config to eval
    return conf
