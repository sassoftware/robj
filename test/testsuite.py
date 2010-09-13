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
import os
import sys

import bootstrap  # pyflakes=ignore

from testrunner import pathManager, testhelp
from testrunner.testhelp import SkipTestException  # pyflakes=ignore

EXCLUDED_PATHS = ['scripts/.*', 'epdb.py', 'stackutil.py', 'test/.*']

def setup():
    pathManager.addExecPath('XOBJ_PATH')
    robjPath = pathManager.addExecPath('ROBJ_PATH')

    pathManager.addResourcePath('TEST_PATH', os.path.join(robjPath, 'test'))
    pathManager.addResourcePath('ROBJ_ARCHIVE_PATH',
        path=os.path.join(robjPath, 'test', 'archive'))

def main(argv=None, individual=True):
    if argv is None:
        argv = list(sys.argv)

    from conary.lib import util
    from conary.lib import coveragehook  # pyflakes=ignore
    sys.excepthook = util.genExcepthook(True, catchSIGUSR1=False)

    handlerClass = testhelp.getHandlerClass(testhelp.ConaryTestSuite,
            lambda handler, environ: os.getenv('ROBJ_PATH'),
            lambda handler, environ: EXCLUDED_PATHS)

    handler = handlerClass(individual=individual)
    results = handler.main(argv)
    return results.getExitCode()


class TestCase(testhelp.TestCase):
    def getArchiveContents(self, filename):
        path = os.path.join(self.archivePath, filename)
        return open(path).read()

    def getResponse(self, uri):
        cclass, pathvars = self.server.controllers.get(uri)
        controller = cclass(self.server.data, None, pathvars)
        response = controller.do_GET()
        return response

    def getModel(self, uri):
        response = self.getResponse(uri)
        return response._model

    def getXML(self, uri):
        response = self.getResponse(uri)
        return response.message

    def setUp(self):
        testhelp.TestCase.setUp(self)

        self.archivePath = pathManager.getPath('ROBJ_ARCHIVE_PATH')

        from robj.lib import log
        log.setupLogging()

        import testserver
        ports = testhelp.findPorts(num=1, closeSockets=True)
        self.server = testserver.ThreadServer(port=ports[0])

    def tearDown(self):
        self.server.shutdown()


if __name__ == '__main__':
    setup()
    sys.exit(main(sys.argv, individual=False))
