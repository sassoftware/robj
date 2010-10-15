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

from robj.http import HTTPClient

class HTTPClientTest(testsuite.TestCase):
    def setUp(self):
        testsuite.TestCase.setUp(self)
        self.client = HTTPClient(self.server.geturi('/api/'), maxClients=1)

    def testGET(self):
        req = self.client.do_GET('/')
        req.wait()

        self.failUnlessEqual(self.getXML('/api'), req.response.content.read())

    def testGETError(self):
        req = self.client.do_GET('/foobar')
        req.wait()

        self.failUnlessEqual(req.response.status, 404)

    def testPOST(self):
        employee1 = self.getArchiveContents('employee1.xml')
        req = self.client.do_POST('/employees', employee1)
        req.wait()

        clientEmployee = req.response.content.read()
        self.failUnlessEqual(clientEmployee, self.getXML('/api/employees/0'))

    def testPOSTError(self):
        employee1 = self.getArchiveContents('employee1.xml')
        req = self.client.do_POST('/', employee1)
        req.wait()

        self.failUnlessEqual(req.response.status, 501)

    def testPUT(self):
        # First post some data so that we can then update it.
        employee1 = self.getArchiveContents('employee1.xml')
        req = self.client.do_POST('/employees', employee1)
        req.wait()

        xml = req.response.content.read()

        # Change the employees name from Fred to Bob.
        xml2 = xml.replace('Fred', 'Bob')

        req2 = self.client.do_PUT('/employees/0', xml2)
        req2.wait()

        respxml = req2.response.content.read()

        self.failUnlessEqual(xml2, respxml)
        self.failUnlessEqual(respxml, self.getXML('/api/employees/0'))

    def testPUTError(self):
        raise testsuite.SkipTestException, ('disable until automated build '
            'failures can be diagnosed')
        req = self.client.do_GET('/')
        req.wait()

        xml = req.response.content.read()
        xml2 = xml.replace('1.0', '2.0')

        req2 = self.client.do_PUT('/', xml2)
        req2.wait()

        self.failUnlessEqual(req2.response.status, 501)

    def testDELETE(self):
        # First post some data so that we can then update it.
        employee1 = self.getArchiveContents('employee1.xml')
        req = self.client.do_POST('/employees', employee1)
        req.wait()

        req2 = self.client.do_DELETE('/employees/0')
        req2.wait()

        self.failUnlessEqual(req2.response.status, 200)

        req3 = self.client.do_DELETE('/employees/0')
        req3.wait()

        self.failUnlessEqual(req3.response.status, 404)

    def testDELETEError(self):
        req = self.client.do_DELETE('/')
        req.wait()

        self.failUnlessEqual(req.response.status, 501)
