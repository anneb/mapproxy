# This file is part of the MapProxy project.
# Copyright (C) 2010 Omniscale <http://omniscale.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import with_statement
import os
import sys
import contextlib

from cStringIO import StringIO
from nose.tools import assert_raises

from mapproxy.client.http import HTTPClient
from mapproxy.script.wms_capabilities import wms_capabilities_command
from mapproxy.test.http import mock_httpd

TESTSERVER_ADDRESS = ('127.0.0.1', 56413)
TESTSERVER_URL = 'http://%s:%s' % TESTSERVER_ADDRESS
CAPABILITIES_FILE = os.path.join(os.path.dirname(__file__), 'fixture', 'util_wms_capabilities.xml')
SERVICE_EXCEPTION_FILE = os.path.join(os.path.dirname(__file__), 'fixture', 'util_wms_capabilities_service_exception.xml')


@contextlib.contextmanager
def capture_out():
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

class TestUtilWMSCapabilities(object):
    def setup(self):
        self.client = HTTPClient()
        self.args = ['command_dummy', '--host', TESTSERVER_URL + '/service']

    def test_http_error(self):
        self.args = ['command_dummy', '--host', 'http://foo.bar']
        with capture_out() as (out,err):
            assert_raises(SystemExit, wms_capabilities_command, self.args)
        assert err.getvalue().startswith("ERROR:")

        self.args[2] = '/no/valid/url'
        with capture_out() as (out,err):
            assert_raises(SystemExit, wms_capabilities_command, self.args)
        assert err.getvalue().startswith("ERROR:")

    def test_request_not_parsable(self):
        with mock_httpd(TESTSERVER_ADDRESS, [({'path': '/service?request=GetCapabilities&version=1.1.1&service=WMS', 'method': 'GET'},
                                              {'status': '200', 'body': ''})]):
            with capture_out() as (out,err):
                assert_raises(SystemExit, wms_capabilities_command, self.args)
            error_msg = err.getvalue().rsplit('-'*80, 1)[1].strip()
            assert error_msg.startswith('Could not parse the document')

    def test_service_exception(self):
        self.args = ['command_dummy', '--host', TESTSERVER_URL + '/service?request=GetCapabilities']
        with open(SERVICE_EXCEPTION_FILE, 'r') as fp:
            capabilities_doc = fp.read()
            with mock_httpd(TESTSERVER_ADDRESS, [({'path': '/service?request=GetCapabilities&version=1.1.1&service=WMS', 'method': 'GET'},
                                                  {'status': '200', 'body': capabilities_doc})]):
                with capture_out() as (out,err):
                    assert_raises(SystemExit, wms_capabilities_command, self.args)
                error_msg = err.getvalue().rsplit('-'*80, 1)[1].strip()
                assert 'Capability element not found' in error_msg

    def test_parse_capabilities(self):
        self.args = ['command_dummy', '--host', TESTSERVER_URL + '/service?request=GetCapabilities']
        with open(CAPABILITIES_FILE, 'r') as fp:
            capabilities_doc = fp.read()
            with mock_httpd(TESTSERVER_ADDRESS, [({'path': '/service?request=GetCapabilities&version=1.1.1&service=WMS', 'method': 'GET'},
                                                  {'status': '200', 'body': capabilities_doc})]):
                with capture_out() as (out,err):
                    wms_capabilities_command(self.args)
                lines = out.getvalue().split('\n')
                assert lines[1].startswith('Root-Layer:')

    def test_key_error(self):
        self.args = ['command_dummy', '--host', TESTSERVER_URL + '/service?request=GetCapabilities']
        with open(CAPABILITIES_FILE, 'r') as fp:
            capabilities_doc = fp.read()
            capabilities_doc = capabilities_doc.replace('minx', 'foo')
            with mock_httpd(TESTSERVER_ADDRESS, [({'path': '/service?request=GetCapabilities&version=1.1.1&service=WMS', 'method': 'GET'},
                                                  {'status': '200', 'body': capabilities_doc})]):
                with capture_out() as (out,err):
                    assert_raises(SystemExit, wms_capabilities_command, self.args)
                error_msg = err.getvalue().rsplit('-'*80, 1)[1].strip()
                assert error_msg.startswith('XML-Element has no such attribute')

