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

import random
import time


class IntervalTimer(object):
    def __init__(self,
                 base_interval,
                 max_interval,
                 backoff_factor=2.7,
                 jitter=.1):
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.next_interval = base_interval
        self.backoff_factor = float(backoff_factor)
        self.jitter = float(jitter)

    def wait(self, event=None, error=False):
        if error:
            next_interval = min(self.next_interval * self.backoff_factor,
                                self.max_interval)
            next_interval = random.normalvariate(next_interval,
                                                 next_interval * self.jitter)
            self.next_interval = next_interval
        else:
            self.next_interval = self.base_interval

        if event:
            return event.wait(self.next_interval)
        else:
            return time.sleep(self.next_interval)
