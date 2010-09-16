#!/usr/bin/python
#
# Copyright (c) 2010 rPath, Inc.
#
# This program is distributed under the terms of the MIT License as found 
# in a file called LICENSE. If it is not present, the license
# is always available at http://www.opensource.org/licenses/mit-license.php.
#
# This program is distributed in the hope that it will be useful, but
# without any waranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the MIT License for full details.
#

import testsuite
testsuite.setup()

from xobj import xobj

from robj import errors
from robj.glue import HTTPClient
from robj.http.request import Response

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

    def testRedirect(self):
        self.failUnlessRaises(NotImplementedError,
            self._client._handle_redirect, None, None, None)

        raise testsuite.SkipTestException, 'Redirects are not yet implemented'

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
