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

        self._client = HTTPClient(self.server.geturi('/api/'), maxClients=1)

    def testGET(self):
        req = self._client.do_GET('/')
        req.wait()

        reqs = []
        for i in range(10):
            reqs.append(self._client.do_GET('/'))

        for req in reqs:
            req.wait()

    def testGETError(self):
        req = self._client.do_GET('/foobar')
        req.wait()

        self.failUnlessEqual(req.resp.status, 404)
