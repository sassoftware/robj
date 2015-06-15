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
from testrunner import testhelp
from robj_test import resources

SkipTestException = testhelp.SkipTestException


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

        self.archivePath = resources.get_archive()

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
