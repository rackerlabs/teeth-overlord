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
import uuid

from requests import Session


class MarconiError(Exception):
    """
    Marconi-related errors.
    """
    pass


class MarconiMessage(object):
    """
    Marconi messages.
    """
    def __init__(self, **kwargs):
        self.body = kwargs.get('body')
        self.ttl = kwargs.get('ttl')
        self.age = kwargs.get('age')
        self.href = kwargs.get('href')


class ClaimedMarconiMessage(MarconiMessage):
    """
    Claimed Marconi messages.
    """
    def __init__(self, **kwargs):
        super(ClaimedMarconiMessage, self).__init__(**kwargs)
        self.claim_href = kwargs.get('claim_href')


class MarconiClient(object):
    """
    A lightweight client to Marconi, based on `requests`.
    """

    USER_AGENT = 'marconi-requests'

    def __init__(self, base_url):
        self.base_url = base_url
        self.client_id = uuid.uuid4()
        self.session = Session()

    def _request(self, method, path, expected_status_codes, params=None, data=None):
        url = '{base_url}{path}'.format(
            base_url=self.base_url,
            path=path,
        )

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': self.USER_AGENT,
            'Client-ID': self.client_id,
        }

        if data:
            body = json.dumps(data)
        else:
            body = None

        response = self.session.request(method, url, headers=headers, data=body, params=params)

        if response.status_code not in expected_status_codes:
            if response.text:
                try:
                    msg = json.loads(response.text)
                except Exception as e:
                    msg = e
            else:
                msg = 'Empty response'

            raise MarconiError(response.status_code, msg)

        return response

    def _request_json(self, *args, **kwargs):
        response = self._request(*args, **kwargs)

        if not response.text:
            raise MarconiError(response.status_code, 'Empty response')
        else:
            try:
                return json.loads(response.text)
            except Exception as e:
                raise MarconiError(response.status_code, e)

    def ensure_queue(self, queue_name):
        """
        Ensure that the specified queue exists.
        """
        path = '/v1/queues/{queue_name}'.format(queue_name=queue_name)
        self._request('PUT', path, [201, 204])

    def push_message(self, queue_name, body, ttl):
        """
        Push a message to the specified queue.
        """
        path = '/v1/queues/{queue_name}/messages'.format(queue_name=queue_name)
        data = [
            {
                'ttl': ttl,
                'body': body,
            }
        ]

        obj = self._request_json('POST', path, [201], data=data)
        return MarconiMessage(body=body, ttl=ttl, age=0, href=obj['resources'][0])
