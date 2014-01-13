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

from carbide_overlord import config
from carbide_overlord import tests

import json
import mock


class MockSource(config.ConfigSource):

    def __init__(self, conf, arg1):
        super(MockSource, self).__init__(conf)
        self._arg1 = arg1

    def get(self, key):
        if key == "FOO":
            return self._arg1
        if key == "BAZ":
            return self._conf.BAZ + 1
        return None


class TestConfig(tests.CarbideMockTestUtilities):
    """Tests for the config object."""

    def test_lazy_config_load_dict(self):
        c = config.LazyConfig(config={"FOO": "BAR", "BAZ": 1})

        self.assertEqual(c.FOO, "BAR")
        self.assertEqual(c["BAZ"], 1)

    def test_lazy_config_load_file(self):
        with mock.patch('__builtin__.open') as my_mock:
            my_mock.return_value.__enter__ = lambda s: s
            my_mock.return_value.__exit__ = mock.Mock()

            conf = {"FOO": "BAR",
                    "BAZ": 1,
                    "FLOAT": 1.5,
                    "LST": [1, 2, 3],
                    "BOOL": True}
            my_mock.return_value.read.return_value = json.dumps(conf)

            c = config.LazyConfig(config_file="foobar")

            for k, v in conf.items():
                self.assertEqual(c[k], v)

    def test_lazy_config_source(self):
        conf = {"FOO": "DEFAULT1", "BAZ": 123,
                "CONFIG_SOURCES": [
                    ["carbide_overlord.tests.unit.config.MockSource", "arg1"]
                ]}
        c = config.LazyConfig(config=conf)

        self.assertEqual(c.FOO, "arg1")
        self.assertEqual(c["BAZ"], 124)

    def test_config_get(self):
        c = config.Config(**{"FOO": 1})

        self.assertEqual(c.get("FOO"), 1)
        self.assertEqual(c.FOO, 1)
        self.assertEqual(c["FOO"], 1)
        self.assertEqual(c.get("BAR", False), None)
        self.assertRaises(ValueError, c.get, "BAR")

    def test_config_set(self):
        c = config.Config()

        c.set("FOO", 1)
        self.assertEqual(c.FOO, 1)

        c.FOO = 2
        self.assertEqual(c["FOO"], 2)

        c["FOO"] = 3
        self.assertEqual(c.get("FOO"), 3)

    def test_config_set_list(self):
        c = config.Config()

        # set list
        c.set("FOO", [1, 2, 3])
        self.assertEqual(c.get("FOO"), [1, 2, 3])

        # set tuple
        c.set("FOO", (4, 5, 6))
        self.assertEqual(c.get("FOO"), (4, 5, 6))

        # set CSV
        c.set("FOO", "7,8,9")
        self.assertEqual(c.get("FOO"), ['7', '8', '9'])

        # set single-item CSV
        c.set("FOO", "10")
        self.assertEqual(c.get("FOO"), ['10'])

        # set invalid type
        self.assertRaises(ValueError, c.set, *("FOO", 1))

    def test_config_set_int(self):
        c = config.Config()

        c.set("FOO", 1)
        self.assertEqual(c.get("FOO"), 1)

        c.FOO = 2
        self.assertEqual(c.FOO, 2)

        c["FOO"] = "3"
        self.assertEqual(c["FOO"], 3)

        self.assertRaises(ValueError, c.set, *("FOO", "a"))

    def test_config_set_float(self):
        c = config.Config()

        c.set("FOO", 1.5)
        self.assertEqual(c.get("FOO"), 1.5)

        c.FOO = 2.5
        self.assertEqual(c.FOO, 2.5)

        c["FOO"] = "3.5"
        self.assertEqual(c["FOO"], 3.5)

        self.assertRaises(ValueError, c.set, *("FOO", "a"))

    def test_config_set_string(self):
        c = config.Config()

        c.set("FOO", "BAR")
        self.assertEqual(c.get("FOO"), "BAR")

        c.FOO = "BAR"
        self.assertEqual(c.FOO, "BAR")

        self.assertRaises(ValueError, c.set, *("FOO", 123))

    def test_config_set_bool(self):
        c = config.Config()

        c.set("FOO", True)
        self.assertEqual(c.get("FOO"), True)

        c.FOO = "true"
        self.assertEqual(c.FOO, True)

        c["FOO"] = 0
        self.assertEqual(c["FOO"], False)

        self.assertRaises(ValueError, c.set, *("FOO", 1234))

    def test_config_set_unicode(self):
        c = config.Config()

        c.set("FOO", u"BAR")
        self.assertEqual(c.get("FOO"), u"BAR")

        c.FOO = u"BAR"
        self.assertEqual(c.FOO, u"BAR")
