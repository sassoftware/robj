#!/usr/bin/python
#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from xobj import xobj

from robj import errors
from robj.glue import HTTPClient
from robj.http.request import Response
from robj_test import robjhelp as testsuite

class ClientTest(testsuite.TestCase):
    def setUp(self):
        testsuite.TestCase.setUp(self)
        self._client = HTTPClient(self.server.geturi('/api/'))

    def testGET(self):
        robj = self._client.do_GET('/')
        api = robj._root

        model = self.getModel('/api')

        # Make sure the xobj that we got from the client layer matches the model
        # on the server side.
        self.failUnlessEqual(api.id, model.id)
        self.failUnlessEqual(api.employees.href, model.employees.href)
        self.failUnlessEqual(api.products.href, model.products.href)
        self.failUnlessEqual(api.version, model.version)

    def testPOST(self):
        # Test POST of an XObj object tree.
        xml = self.getArchiveContents('employee1.xml')
        doc = xobj.parse(xml)
        model = doc.employee

        robj = self._client.do_POST('/employees', model)
        employee = robj._root

        # Make sure the model that is returned matches the one that was sent.
        self.failUnlessEqual(model.name, employee.name)
        self.failUnlessEqual(model.address.street, employee.address.street)
        self.failUnlessEqual(model.address.city, employee.address.city)
        self.failUnlessEqual(model.address.state, employee.address.state)
        self.failUnlessEqual(model.address.zipcode, employee.address.zipcode)
        self.failUnlessEqual(model.phone, employee.phone)
        self.failUnlessEqual(employee.employeeid, '0')
        self.failUnlessEqual(employee.id, '/api/employees/0')

        # Make sure there is an error raised when no document is provided.
        self.failUnlessRaises(TypeError, self._client.do_POST, '/employees')

        # Make sure POST of an XObj document works.
        xml2 = self.getArchiveContents('employee2.xml')
        doc2 = xobj.parse(xml2)

        robj = self._client.do_POST('/employees', doc2)
        employee2 = robj._root

        self.failUnlessEqual(doc2.employee.name, employee2.name)
        self.failUnlessEqual(employee2.employeeid, '1')

    def testPUT(self):
        xml = self.getArchiveContents('employee1.xml')
        doc = xobj.parse(xml)
        model = doc.employee

        # Start by creating the resource
        robj = self._client.do_POST('/employees', model)
        employee = robj._root

        # Make sure the resource matches what we posted
        self.failUnlessEqual(model.phone, employee.phone)

        # Change the phone number.
        employee.phone = '12345'
        robj = self._client.do_PUT(employee.id, employee)
        employee2 = robj._root

        self.failIfEqual(model.phone, employee.phone)
        self.failUnlessEqual(employee.phone, employee2.phone)

    def testDELETE(self):
        xml = self.getArchiveContents('employee1.xml')
        doc = xobj.parse(xml)

        uri = self._client.do_POST('/employees', doc)._root.id

        response = self._client.do_DELETE(uri)
        self.failUnlessEqual(response.status, 200)

        response2 = self._client.do_DELETE(uri)
        self.failUnlessEqual(response2.status, 404)

    def testDELETE204(self):
        xml = self.getArchiveContents('product1.xml')
        doc = xobj.parse(xml)

        uri = self._client.do_POST('/products', doc)._root.id

        response = self._client.do_DELETE(uri)
        self.failUnlessEqual(response.status, 204)

        response2 = self._client.do_DELETE(uri)
        self.failUnlessEqual(response2.status, 404)

    def testRedirect(self):
        def testFail(eclass, path):
            self.failUnlessRaises(eclass, self._client.do_GET, path)
        def clearCache():
            self._client.cache.clear()
            self._client._redirects = {}

        error = errors.HTTPUnhandledRedirectError
        testFail(error, '/redirects/300')
        testFail(error, '/redirects/305')

        obj = self._client.do_GET('/redirects/301')
        self.failUnless('/redirects/301' in self._client._redirects)
        self.failUnless(obj in self._client.cache.values())
        self.failUnlessEqual(obj._uri,
            self._client._redirects['/redirects/301'])

        clearCache()

        obj = self._client.do_GET('/redirects/302')
        self.failIf('/redirects/302' in self._client._redirects)
        self.failUnless(obj in self._client.cache.values())
        self.failUnlessEqual(obj._uri, '/redirects/302')

        clearCache()

        obj = self._client.do_GET('/redirects/303')
        self.failIf('/redirects/303' in self._client._redirects)
        self.failUnless(obj in self._client.cache.values())
        self.failUnlessEqual(obj._uri, '/employees')

        clearCache()

        obj = self._client.do_GET('/redirects/304')
        self.failIf('/redirects/304' in self._client._redirects)
        self.failUnless(obj in self._client.cache.values())
        self.failUnlessEqual(obj._uri, '/redirects/304')

        clearCache()

        obj = self._client.do_GET('/redirects/307')
        self.failIf('/redirects/307' in self._client._redirects)
        self.failIf(obj in self._client.cache.values())
        self.failUnlessEqual(obj._uri, '/redirects/307')

        clearCache()

        self.failUnlessRaises(errors.HTTPMaxRedirectReachedError,
            self._client.do_GET, '/redirects/loop')

        self.failUnlessRaises(errors.HTTPMaxRedirectReachedError,
            self._client.do_GET, '/redirects/1')

    def testErrors(self):
        # test delete error path
        self.failUnlessRaises(errors.HTTPDeleteError,
            self._client.do_DELETE, '/')

        # test normal error path
        self.failUnlessRaises(errors.HTTPNotImplementedError,
            self._client.do_POST, '/', '')

        # test ignored error path
        self._client.error_exceptions[404] = None
        response = self._client.do_GET('/foobar')
        self.failUnless(isinstance(response, Response))

    def testNormalizeUri(self):
        path = self._client._client.path
        baseUri = self._client._client.baseURI

        tests = (
            (baseUri + '/foobar', '/foobar'),
            (path + '/foobar', '/foobar'),
            ('/foobar/', '/foobar'),
        )

        for input, expected in tests:
            self.failUnlessEqual(self._client._normalize_uri(input), expected)

        self.failUnlessRaises(errors.ExternalUriError,
            self._client._normalize_uri, 'httpd://foobar')

    def testSerialize(self):
        self.failUnlessRaises(errors.SerializationError,
            self._client._serialize_document, object())
