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


import os
import sys

import bootstrap  # pyflakes=ignore

from testrunner import pathManager, testhelp
from testrunner.testhelp import SkipTestException  # pyflakes=ignore

EXCLUDED_PATHS = ['scripts/.*', 'epdb.py', 'stackutil.py', 'test/.*']

from testrunner import suite


class Suite(suite.TestSuite):
    testsuite_module = sys.modules[__name__]
    topLevelStrip = 0

    def setup(self):
        suite.TestSuite.setup(self)
        pathManager.addExecPath('XOBJ_PATH')
        pathManager.addExecPath('ROBJ_PATH')

        robjTestPath = pathManager.addExecPath('ROBJ_TEST_PATH')
        pathManager.addExecPath('TEST_PATH', path=robjTestPath)
        pathManager.addResourcePath('ROBJ_ARCHIVE_PATH',
            path=os.path.join(robjTestPath, 'archive'))

    def setupModules(self):
        pass

    def getCoverageDirs(self, handler, environ):
        import robj
        return [robj]


_s = Suite()
setup = _s.setup
main = _s.main


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

    def run(self, results=None):
        if results is not None:
            self._debug_flag = results.debug
        return testhelp.TestCase.run(self, results)

    def setUp(self):
        testhelp.TestCase.setUp(self)

        self.archivePath = pathManager.getPath('ROBJ_ARCHIVE_PATH')

        import testserver
        ports = testhelp.findPorts(num=1, closeSockets=True)
        self.server = testserver.ThreadServer(port=ports[0],
            debug=self._debug_flag)

        import logging
        log = logging.getLogger('robj.http.traffic')
        self._old_log_level = log.level

        if self._debug_flag:
            log.setLevel(logging.DEBUG)

    def tearDown(self):
        # On python 2.6 we can shutdown the socket server
        if hasattr(self.server, 'shutdown'):
            self.server.shutdown()

        import logging
        log = logging.getLogger('robj.http.traffic')
        log.setLevel(self._old_log_level)

        testhelp.TestCase.tearDown(self)


if __name__ == '__main__':
    _s.run()
