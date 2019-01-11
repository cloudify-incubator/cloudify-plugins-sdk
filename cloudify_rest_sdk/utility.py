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

import yaml
import logging
import ast
import re
import xmltodict
from jinja2 import Template
import requests

from cloudify_rest_sdk import LOGGER_NAME
from cloudify_common_sdk.filters import translate_and_save
from cloudify_common_sdk.exceptions import (
    RecoverableStatusCodeCodeException,
    ExpectationException,
    WrongTemplateDataException,
    NonRecoverableResponseException,
    RecoverableResponseException)

logger = logging.getLogger(LOGGER_NAME)

TEMPLATE_PROPERTY_RETRY_ON_CONNECTION_ERROR = 'retry_on_connection_error'


#  request_props (port, ssl, verify, hosts )
def process(params, template, request_props):
    logger.info('Template:\n{}...'.format(str(template)[:4096]))
    template_yaml = yaml.load(template)
    result_properties = {}
    calls = []
    for call in template_yaml['rest_calls']:
        call_with_request_props = request_props.copy()
        logger.debug('Call \n {}'.format(call))
        # enrich params with items stored in runtime props by prev calls
        params.update(result_properties)
        call = str(call)
        # Remove quotation marks before and after jinja blocks
        call = re.sub(r'\'\{\%', '{%', call)
        call = re.sub(r'\%\}\'', '%}', call)
        template_engine = Template(call)
        rendered_call = template_engine.render(params)
        call = ast.literal_eval(rendered_call)
        calls.append(call)
        logger.debug('Rendered call: {}'.format(repr(call)))
        call_with_request_props.update(call)
        response = _send_request(call_with_request_props)
        _process_response(response, call, result_properties)
    result_properties = {'result_properties': result_properties,
                         'calls': calls}
    return result_properties


def _send_request(call, resource_callback=None):
    logger.debug('Request props: {}'.format(repr(call)))
    port = call['port']
    ssl = call['ssl']
    if port == -1:
        port = 443 if ssl else 80
    if not call.get('hosts', None):
        call['hosts'] = [call['host']]
    for i, host in enumerate(call['hosts']):
        full_url = '{}://{}:{}{}'.format('https' if ssl else 'http', host,
                                         port,
                                         call['path'])
        logger.debug('Full url: {}'.format(repr(full_url)))
        # check if payload can be used as json
        payload_format = call.get('payload_format', 'json')
        payload_data = call.get('payload', None)
        params = call.get('params', {})
        if payload_format == 'json':
            json_payload = payload_data
            data = None
        elif payload_format == 'urlencoded' and isinstance(payload_data, dict):
            json_payload = None
            params.update(payload_data)
            data = None
        else:
            json_payload = None
            data = payload_data

        try:
            response = requests.request(call['method'], full_url,
                                        headers=call.get('headers', None),
                                        verify=call.get('verify', True),
                                        json=json_payload,
                                        params=params,
                                        data=data)
        except requests.exceptions.ConnectionError as e:
            logger.debug('ConnectionError for host: {}'.format(repr(host)))

            if TEMPLATE_PROPERTY_RETRY_ON_CONNECTION_ERROR in call and \
                    call[TEMPLATE_PROPERTY_RETRY_ON_CONNECTION_ERROR]:

                raise RecoverableResponseException(
                    'ConnectionError {0} has occurred, but flag {1} is set. '
                    'Retrying...'
                    .format(
                        str(e),
                        TEMPLATE_PROPERTY_RETRY_ON_CONNECTION_ERROR
                    )
                )

            if i == len(call['hosts']) - 1:
                logger.error('No host from list available')
                raise

    logger.info('Response content: \n{}...'
                .format(str(response.content)[:4096]))
    logger.info('Status code: {}'.format(repr(response.status_code)))

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.debug(repr(e))
        if response.status_code in call.get('recoverable_codes', []):
            raise RecoverableStatusCodeCodeException(
                'Response code {} defined as recoverable'.format(
                    response.status_code))
        raise
    return response


def _process_response(response, call, store_props):
    logger.debug('Process Response: {}'.format(repr(response)))
    logger.debug('Call: {}'.format(repr(call)))
    logger.debug('Store props: {}'.format(repr(store_props)))
    logger.debug('Store headers: {}'.format(repr(response.headers)))
    translation_version = call.get('translation_format', 'auto')

    # process headers
    if response.headers:
        translate_and_save(logger, response.headers,
                           call.get('header_translation', None),
                           store_props, translation_version)
    # process cookies
    if response.cookies:
        translate_and_save(logger, response.cookies.get_dict(),
                           call.get('cookies_translation', None),
                           store_props, translation_version)
    # process body
    response_format = call.get('response_format', 'auto').lower()
    if response_format == 'auto':
        if response.headers.get('Content-Type'):
            response_content_type = response.headers['Content-Type'].lower()
            if response_content_type.startswith("application/json"):
                response_format = 'json'
            elif (
                response_content_type.startswith('text/xml') or
                response_content_type.startswith('application/xml')
            ):
                response_format = 'xml'
            logger.debug('Detected type is {}'.format(repr(response_format)))
    logger.debug('Response format is {}'.format(repr(response_format)))
    if response_format == 'json' or response_format == 'xml':
        if response_format == 'json':
            json = response.json()
        else:  # XML
            json = xmltodict.parse(response.text)
            logger.debug('XML transformed to dict: {}'.format(repr(json)))

        _check_response(json, call.get('nonrecoverable_response'), False)
        _check_response(json, call.get('response_expectation'), True)

        translate_and_save(logger, json,
                           call.get('response_translation', None),
                           store_props, translation_version)
    elif response_format == 'text':
        store_props['text'] = response.text
    elif response_format == 'raw':
        logger.debug('No action for raw response_format')
    else:
        raise WrongTemplateDataException(
            "Response_format {} is not supported. "
            "Only json/xml or raw response_format is supported".format(
                repr(response_format)))


def _check_response(json, response, is_recoverable):
    if not is_recoverable:
        logger.debug('Check response (nonrecoverable) in json: {} by {}'
                     .format(repr(json), repr(response)))
    else:
        logger.debug('Check response (recoverable) in json: {} by {}'
                     .format(repr(json), repr(response)))

    if not response:
        return

    if not isinstance(response, list) and not is_recoverable:
        raise WrongTemplateDataException(
            "Response (nonrecoverable) had to be list. "
            "Type {} not supported. ".format(
                type(response)))

    if not isinstance(response, list) and is_recoverable:
        raise WrongTemplateDataException(
            "Response (recoverable) had to be list. "
            "Type {} not supported. ".format(
                type(response)))

    if isinstance(response[0], list):
        for item in response:
            _check_response(json, item, is_recoverable)
    else:
        pattern = response.pop(-1)
        for key in response:

            try:
                json = json[key]
            except (TypeError, IndexError, KeyError) as e:
                logger.debug(repr(e))
                raise ExpectationException(
                        'No key or index "{}" in json {}'.format(key, json))

        if re.match(str(pattern), str(json)) and not is_recoverable:
            raise NonRecoverableResponseException(
                "Giving up... \n"
                "Response value: "
                "{} matches regexp:{} from nonrecoverable_response. ".format(
                    str(json), str(pattern)))
        if not re.match(str(pattern), str(json)) and is_recoverable:
            raise RecoverableResponseException(
                "Trying one more time...\n"
                "Response value:{} does not match regexp: {} "
                "from response_expectation".format(
                    str(json), str(pattern)))
