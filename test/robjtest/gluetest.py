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

from robj.glue import HTTPClient

class ClientTest(testsuite.TestCase):
    def setUp(self):
        testsuite.TestCase.setUp(self)
        self._client = HTTPClient('http://www.rpath.org/api/')

    def testGET(self):
        api = self._client.do_GET('/')
        prodMap = dict([ (x.hostname, x) for x in api.products ])
        buildme = prodMap['buildme']
        versions = buildme.versions

        imageTypeDefs = {}
        for version in buildme.versions:
            for imgDef in version.imageTypeDefinitions:
                imageTypeDefs.setdefault(version.name, set()).add(imgDef.name)

        images = versions[0].images

        img1 = images[0]
        files = img1.files

        for f in files:
            print 80 * '='
            for e in f.elements:
                print '%s: %s' % (e, getattr(f, e))

        import epdb; epdb.st()


