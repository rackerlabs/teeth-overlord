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

import requests


def post(path, item):
    url = 'http://localhost:8080' + path
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json.dumps(item), headers=headers)
    return response.headers.get('location').rsplit('/')[-1]


def run():
    requests.put('http://localhost:8888/v1/queues/carbide_jobs')
    chassis_model_id = post('/v1/chassis_models', {
        'name': 'Supermicro  1027R-WRFT+',
        'default_ipmi_username': 'ADMIN',
        'default_ipmi_password': 'ADMIN',
    })
    flavor_id = post('/v1/flavors', {
        'name': 'Fast Server A',
    })
    post('/v1/flavor_providers', {
        'chassis_model_id': chassis_model_id,
        'flavor_id': flavor_id,
        'schedule_priority': 100,
    })
    for i in xrange(0, 15):
        post('/v1/chassis', {
            'chassis_model_id': chassis_model_id,
            'primary_mac_address': 'a:b:c:d',
        })
