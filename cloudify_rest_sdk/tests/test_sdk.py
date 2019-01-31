########
# Copyright (c) 2014-2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import unittest
import json
import mock

from cloudify_rest_sdk import utility
from cloudify_common_sdk import exceptions


class TestSdk(unittest.TestCase):

    def test_check_response(self):
        parsed_json = json.loads('''{
            "id": 10,
            "name": "Clementina DuBuque",
            "username": "Moriah.Stanton",
            "email": "Rey.Padberg@karina.biz",
            "address": {
                "street": "Kattie Turnpike",
                "suite": "Suite 198",
                "city": "Lebsackbury",
                "zipcode": "31428-2261",
                "geo": {
                    "lat": "-38.2386",
                    "lng": "57.2232"
                }
            },
            "phone": "024-648-3804",
            "website": "ambrose.net",
            "company": {
                "name": "Hoeger LLC",
                "catchPhrase": "Centralized empowering task-force",
                "bs": "target end-to-end models"
            }
        }''')
        # no check, should be skiped
        utility._check_response(parsed_json, [], True)
        # correct check
        utility._check_response(parsed_json, [['id', '10']], True)
        # incorect data / Recoverable, filter that data not match
        with self.assertRaises(
            exceptions.RecoverableResponseException
        ) as error:
            utility._check_response(parsed_json, [['id', '22']], True)
        self.assertEqual(
            str(error.exception),
            'Trying one more time...\nResponse value:10 does not match '
            'regexp: 22 from response_expectation')
        # incorect data / NonRecoverable, filter that data match
        with self.assertRaises(
            exceptions.NonRecoverableResponseException
        ) as error:
            utility._check_response(parsed_json, [['id', '10']], False)
        self.assertEqual(
            str(error.exception),
            'Giving up... \nResponse value: 10 matches regexp:10 from '
            'nonrecoverable_response. ')
        # correct data, filter that data not match
        utility._check_response(parsed_json, [['id', '20']], False)
        # wrond data structure
        error_text = 'No key or index "id" in json [{\'id\': 40}]'
        with self.assertRaises(
            exceptions.ExpectationException
        ) as error:
            utility._check_response([{'id': 40}], [['id', '20']], False)
        self.assertEqual(str(error.exception), error_text)
        with self.assertRaises(
            exceptions.ExpectationException
        ) as error:
            utility._check_response([{'id': 40}], [['id', '20']], True)
        self.assertEqual(str(error.exception), error_text)
        # wrong checked
        with self.assertRaises(
            exceptions.WrongTemplateDataException
        ) as error:
            utility._check_response([{'id': 40}], 'AAAA', True)
        self.assertEqual(
            str(error.exception),
            "Response (recoverable) had to be list. Type <type 'str'> "
            "not supported. ")
        with self.assertRaises(
            exceptions.WrongTemplateDataException
        ) as error:
            utility._check_response([{'id': 40}], 'AAAA', False)
        self.assertEqual(
            str(error.exception),
            "Response (nonrecoverable) had to be list. Type <type 'str'> "
            "not supported. ")

    def test_process_response(self):
        parsed_json = json.loads('''{
            "id": 10,
            "name": "Clementina DuBuque",
            "username": "Moriah.Stanton",
            "email": "Rey.Padberg@karina.biz",
            "address": {
                "street": "Kattie Turnpike",
                "suite": "Suite 198",
                "city": "Lebsackbury",
                "zipcode": "31428-2261",
                "geo": {
                    "lat": "-38.2386",
                    "lng": "57.2232"
                }
            },
            "phone": "024-648-3804",
            "website": "ambrose.net",
            "company": {
                "name": "Hoeger LLC",
                "catchPhrase": "Centralized empowering task-force",
                "bs": "target end-to-end models"
            }
        }''')
        response = mock.Mock()
        response.json = mock.Mock(return_value=parsed_json)
        response.text = '''<object>10</object>'''
        response.headers = {
            'Content-Type': "application/json"
        }
        response.cookies = mock.Mock()
        response.cookies.get_dict = mock.Mock(return_value={'a': 'b'})
        # json
        store_props = {}
        call = {
            'response_format': 'json',
            'nonrecoverable_response': [['id', '20']],
            'response_expectation': [['id', '10']],
            'response_translation': {
                "name": ["user-full-name"],
                "email": ["user-email"],
                "address": {
                    "city": ["user-city"],
                    "zipcode": ["user-city-zip"],
                    "geo": {
                        "lat": ["user-city-geo", "latitude"],
                        "lng": ["user-city-geo", "longnitude"]
                    }
                }
            }
        }
        utility._process_response(response, call, store_props)
        self.assertDictEqual(store_props, {
            'user-city': u'Lebsackbury',
            'user-city-geo': {
                'latitude': u'-38.2386',
                'longnitude': u'57.2232'
            },
            'user-city-zip': u'31428-2261',
            'user-email': u'Rey.Padberg@karina.biz',
            'user-full-name': u'Clementina DuBuque'
        })
        # auto json
        store_props = {}
        call = {
            'nonrecoverable_response': [['id', '20']],
            'response_expectation': [['id', '10']],
            'response_translation': {
                "name": ["user-full-name"],
                "email": ["user-email"],
                "address": {
                    "city": ["user-city"],
                    "zipcode": ["user-city-zip"],
                    "geo": {
                        "lat": ["user-city-geo", "latitude"],
                        "lng": ["user-city-geo", "longnitude"]
                    }
                }
            }
        }
        utility._process_response(response, call, store_props)
        self.assertDictEqual(store_props, {
            'user-city': u'Lebsackbury',
            'user-city-geo': {
                'latitude': u'-38.2386',
                'longnitude': u'57.2232'
            },
            'user-city-zip': u'31428-2261',
            'user-email': u'Rey.Padberg@karina.biz',
            'user-full-name': u'Clementina DuBuque'
        })
        # raw response
        store_props = {}
        call = {
            'response_format': 'raw',
        }
        utility._process_response(response, call, store_props)
        self.assertDictEqual(store_props, {})
        # text response
        store_props = {}
        call = {
            'response_format': 'text',
        }
        utility._process_response(response, call, store_props)
        self.assertDictEqual(store_props, {'text': '<object>10</object>'})
        # unknown response
        store_props = {}
        call = {
            'response_format': 'other',
        }
        with self.assertRaises(
            exceptions.WrongTemplateDataException
        ) as error:
            utility._process_response(response, call, store_props)
        self.assertEqual(
            str(error.exception),
            "Response_format 'other' is not supported. Only json/xml or raw "
            "response_format is supported")
        self.assertDictEqual(store_props, {})
        # xml response
        store_props = {}
        call = {
            'response_format': 'xml',
            'nonrecoverable_response': [['object', '20']],
            'response_expectation': [['object', '10']],
            'response_translation': {
                "object": ["object_id"]
            }
        }
        utility._process_response(response, call, store_props)
        self.assertDictEqual(store_props, {'object_id': '10'})
        # auto xml response
        response.headers = {
            'Content-Type': 'application/xml'
        }
        store_props = {}
        call = {
            'nonrecoverable_response': [['object', '20']],
            'response_expectation': [['object', '10']],
            'response_translation': {
                "object": ["object_id"]
            },
            'header_translation': {
                "Content-Type": ["content_type"]
            }
        }
        utility._process_response(response, call, store_props)
        self.assertDictEqual(store_props, {'object_id': '10',
                                           'content_type': 'application/xml'})
        # can't use autodetected type, failback to json
        response.headers = {
            'Content-Type': "json-alias"
        }
        store_props = {}
        call = {
            'nonrecoverable_response': [['id', '20']],
            'response_expectation': [['id', '10']],
            'response_translation': {
                "name": ["user-full-name"],
                "email": ["user-email"],
                "address": {
                    "city": ["user-city"],
                    "zipcode": ["user-city-zip"],
                    "geo": {
                        "lat": ["user-city-geo", "latitude"],
                        "lng": ["user-city-geo", "longnitude"]
                    }
                }
            }
        }
        utility._process_response(response, call, store_props)
        self.assertDictEqual(store_props, {
            'user-city': u'Lebsackbury',
            'user-city-geo': {
                'latitude': u'-38.2386',
                'longnitude': u'57.2232'
            },
            'user-city-zip': u'31428-2261',
            'user-email': u'Rey.Padberg@karina.biz',
            'user-full-name': u'Clementina DuBuque'
        })

    def test_send_request(self):
        # json request
        call = {
            'ssl': True,
            'path': "/",
            'method': 'get',
            'verify': False,
            'host': 'localhost',
            'auth': {
                'user': 'someone',
                'password': 'check'
            },
            'port': -1,
            'payload': [1, 2, 3],
            'headers': {"a": "b"},
            'response_format': 'xml',
            'nonrecoverable_response': [['object', '20']],
            'response_expectation': [['object', '10']],
            'response_translation': {
                "object": ["object_id"]
            }
        }
        response = mock.Mock()
        response.json = None
        response.raise_for_status = mock.Mock()
        response.text = '''<object>10</object>'''
        request = mock.Mock(return_value=response)
        response.headers = {}
        response.cookies = mock.Mock()
        response.cookies.get_dict = mock.Mock(return_value={'a': 'b'})
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            self.assertEqual(utility._send_request(call), response)
        request.assert_called_with('get', 'https://localhost:443/',
                                   data=None, headers={'a': 'b'},
                                   json=[1, 2, 3],
                                   params={},
                                   auth=('someone', 'check'),
                                   verify=False)

        # xml request
        call = {
            'ssl': True,
            'path': "/xml",
            'method': 'get',
            'verify': False,
            'host': 'localhost',
            'port': -1,
            'payload': '<object>11</object>',
            'payload_format': 'raw',
            'headers': {"a": "b"},
            'response_format': 'xml',
            'nonrecoverable_response': [['object', '20']],
            'response_expectation': [['object', '10']],
            'response_translation': {
                "object": ["object_id"]
            }
        }
        response = mock.Mock()
        response.json = None
        response.raise_for_status = mock.Mock()
        response.text = '''<object>10</object>'''
        response.status_code = 404
        response.headers = {}
        response.cookies = mock.Mock()
        response.cookies.get_dict = mock.Mock(return_value={'a': 'b'})
        request = mock.Mock(return_value=response)
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            self.assertEqual(utility._send_request(call), response)
        request.assert_called_with('get', 'https://localhost:443/xml',
                                   data='<object>11</object>',
                                   headers={'a': 'b'},
                                   json=None,
                                   params={},
                                   auth=None,
                                   verify=False)

        # raise error on request status
        response.raise_for_status = mock.Mock(
            side_effect=utility.requests.exceptions.HTTPError('Error!')
        )
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            with self.assertRaises(
                utility.requests.exceptions.HTTPError
            ) as error:
                self.assertEqual(utility._send_request(call), response)
            self.assertEqual(str(error.exception), 'Error!')

        # expected error
        call['recoverable_codes'] = [404]
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            with self.assertRaises(
                exceptions.RecoverableStatusCodeCodeException
            ) as error:
                self.assertEqual(utility._send_request(call), response)
            self.assertEqual(
                str(error.exception),
                'Response code 404 defined as recoverable')

        # can't connect
        request = mock.Mock(
            side_effect=utility.requests.exceptions.ConnectionError(
                'check connect')
        )
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            with self.assertRaises(
                utility.requests.exceptions.ConnectionError
            ) as error:
                self.assertEqual(utility._send_request(call), response)
            self.assertEqual(str(error.exception), "check connect")

        # ignore conenction errors
        call['retry_on_connection_error'] = True
        request = mock.Mock(
            side_effect=utility.requests.exceptions.ConnectionError(
                'check connect')
        )
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            with self.assertRaises(
                exceptions.RecoverableResponseException
            ) as error:
                self.assertEqual(utility._send_request(call), response)
            self.assertEqual(
                str(error.exception),
                "ConnectionError check connect has occurred, but flag "
                "retry_on_connection_error is set. Retrying...")

    def test_process_pre_render(self):
        # without params
        template = """
            rest_calls:
            - ssl: true
              path: "/xml"
              method: get
              verify: false
              host: localhost
              port: -1
              payload: {{ payload }}
              payload_format: raw
              headers:
                a: b
              response_format: xml
              nonrecoverable_response: [['object', '20']]
              response_expectation: [['object', '10']]
              response_translation:
                object:
                - object_id"""
        response = mock.Mock()
        response.json = None
        response.raise_for_status = mock.Mock()
        response.text = '''<object>10</object>'''
        response.status_code = 404
        response.headers = {
            'Content-Type': "application/json"
        }
        response.cookies = mock.Mock()
        response.cookies.get_dict = mock.Mock(return_value={'a': 'b'})
        request = mock.Mock(return_value=response)
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            self.assertEqual(
                utility.process({'payload': '<object>11</object>'}, template,
                                {}, prerender=True), {
                    'calls': [{
                        'headers': {'a': 'b'},
                        'host': 'localhost',
                        'method': 'get',
                        'nonrecoverable_response': [['object']],
                        'path': '/xml',
                        'payload': '<object>11</object>',
                        'payload_format': 'raw',
                        'port': -1,
                        'response_expectation': [['object']],
                        'response_format': 'xml',
                        'response_translation': {'object': []},
                        'ssl': True,
                        'verify': False
                    }],
                    'result_properties': {'object_id': u'10'}})
        request.assert_called_with('get', 'https://localhost:443/xml',
                                   data='<object>11</object>',
                                   headers={'a': 'b'},
                                   json=None,
                                   params={},
                                   auth=None,
                                   verify=False)
        # check rawpayload
        template = """
            rest_calls:
            - ssl: true
              path: "/xml"
              method: get
              verify: false
              host: localhost
              port: -1
              raw_payload: payload.xml
              payload: {{ payload }}
              payload_format: raw
              headers:
                a: b
              response_format: xml
              nonrecoverable_response: [['object', '20']]
              response_expectation: [['object', '10']]
              response_translation:
                object:
                - object_id"""
        payload_callback = mock.Mock(return_value="<object>22</object>")
        response = mock.Mock()
        response.json = None
        response.raise_for_status = mock.Mock()
        response.text = '''<object>10</object>'''
        response.status_code = 404
        response.headers = {
            'Content-Type': "application/json"
        }
        response.cookies = mock.Mock()
        response.cookies.get_dict = mock.Mock(return_value={'a': 'b'})
        request = mock.Mock(return_value=response)
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            self.assertEqual(
                utility.process({'payload': '<object>11</object>'}, template,
                                {}, prerender=True,
                                resource_callback=payload_callback), {
                    'calls': [{
                        'headers': {'a': 'b'},
                        'host': 'localhost',
                        'method': 'get',
                        'nonrecoverable_response': [['object']],
                        'path': '/xml',
                        'raw_payload': 'payload.xml',
                        'payload': '<object>11</object>',
                        'payload_format': 'raw',
                        'port': -1,
                        'response_expectation': [['object']],
                        'response_format': 'xml',
                        'response_translation': {'object': []},
                        'ssl': True,
                        'verify': False
                    }],
                    'result_properties': {'object_id': u'10'}})
        request.assert_called_with('get', 'https://localhost:443/xml',
                                   data='<object>22</object>',
                                   headers={'a': 'b'},
                                   json=None,
                                   params={},
                                   auth=None,
                                   verify=False)
        payload_callback.assert_called_with('payload.xml')

    def test_process_empty(self):
        # no calls in template
        template = """
            rest_calls:
        """
        self.assertEqual(utility.process({}, template, {}), {})
        # empty template
        self.assertEqual(utility.process({}, "", {}), {})

    def test_process_post_render(self):
        # without params
        template = """
            rest_calls:
            - ssl: true
              path: "/xml"
              method: get
              verify: false
              host: localhost
              port: -1
              payload: '<object>11</object>'
              payload_format: raw
              headers:
                a: b
              response_format: xml
              nonrecoverable_response: [['object', '20']]
              response_expectation: [['object', '10']]
              response_translation:
                object:
                - object_id"""
        response = mock.Mock()
        response.json = None
        response.raise_for_status = mock.Mock()
        response.text = '''<object>10</object>'''
        response.status_code = 404
        response.headers = {
            'Content-Type': "application/json"
        }
        response.cookies = mock.Mock()
        response.cookies.get_dict = mock.Mock(return_value={'a': 'b'})
        request = mock.Mock(return_value=response)
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            self.assertEqual(
                utility.process({}, template, {}), {
                    'calls': [{
                        'headers': {'a': 'b'},
                        'host': 'localhost',
                        'method': 'get',
                        'nonrecoverable_response': [['object']],
                        'path': '/xml',
                        'payload': '<object>11</object>',
                        'payload_format': 'raw',
                        'port': -1,
                        'response_expectation': [['object']],
                        'response_format': 'xml',
                        'response_translation': {'object': []},
                        'ssl': True,
                        'verify': False
                    }],
                    'result_properties': {'object_id': u'10'}})
        request.assert_called_with('get', 'https://localhost:443/xml',
                                   data='<object>11</object>',
                                   headers={'a': 'b'},
                                   json=None,
                                   params={},
                                   auth=None,
                                   verify=False)
        # check post apply parameters
        template = """
            rest_calls:
            - ssl: true
              path: "/xml"
              method: get
              verify: false
              host: localhost
              port: -1
              payload: "{% if custom is not string %}{{custom}}{% endif %}"
              payload_format: raw
              headers:
                a: b
              response_format: xml
              nonrecoverable_response: [['object', '20']]
              response_expectation: [['object', '10']]
              response_translation:
                object:
                - object_id"""
        request = mock.Mock(return_value=response)
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            self.assertEqual(
                utility.process({'custom': [1, 2, 3]}, template,
                                {}, ), {
                    'calls': [{
                        'headers': {'a': 'b'},
                        'host': 'localhost',
                        'method': 'get',
                        'nonrecoverable_response': [['object']],
                        'path': '/xml',
                        'payload': [1, 2, 3],
                        'payload_format': 'raw',
                        'port': -1,
                        'response_expectation': [['object']],
                        'response_format': 'xml',
                        'response_translation': {'object': []},
                        'ssl': True,
                        'verify': False
                    }],
                    'result_properties': {'object_id': u'10'}})
        request.assert_called_with('get', 'https://localhost:443/xml',
                                   data=[1, 2, 3],
                                   headers={'a': 'b'},
                                   json=None,
                                   params={},
                                   auth=None,
                                   verify=False)
        # urlencode
        template = """
            rest_calls:
            - ssl: true
              path: "/xml"
              method: get
              verify: false
              host: localhost
              port: -1
              payload:
                object: 11
              payload_format: urlencoded
              headers:
                a: b
              response_format: xml
              nonrecoverable_response: [['object', '20']]
              response_expectation: [['object', '10']]
              cookies_translation:
                a:
                - a
              response_translation:
                object:
                - object_id"""
        response = mock.Mock()
        response.json = None
        response.raise_for_status = mock.Mock()
        response.text = '''<object>10</object>'''
        response.status_code = 404
        response.headers = {
            'Content-Type': "application/json"
        }
        response.cookies = mock.Mock()
        response.cookies.get_dict = mock.Mock(return_value={'a': 'b'})
        request = mock.Mock(return_value=response)
        with mock.patch(
            "cloudify_rest_sdk.utility.requests.request", request
        ):
            self.assertEqual(
                utility.process({}, template, {}),
                {
                    'calls': [{
                        'headers': {'a': 'b'},
                        'host': 'localhost',
                        'method': 'get',
                        'nonrecoverable_response': [['object']],
                        'path': '/xml',
                        'payload': {
                            'object': 11
                        },
                        'payload_format': 'urlencoded',
                        'port': -1,
                        'response_expectation': [['object']],
                        'response_format': 'xml',
                        'response_translation': {'object': []},
                        'cookies_translation': {'a': []},
                        'ssl': True,
                        'verify': False
                    }],
                    'result_properties': {
                        'object_id': '10',
                        'a': 'b'
                    }})
        request.assert_called_with('get', 'https://localhost:443/xml',
                                   data=None,
                                   headers={'a': 'b'},
                                   json=None,
                                   params={'object': 11},
                                   auth=None,
                                   verify=False)


if __name__ == '__main__':
    unittest.main()
