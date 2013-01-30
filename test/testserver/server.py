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
import logging
from threading import Thread
from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from testserver import models
from testserver.datastore import DataStore
from testserver.controllers import controllers

log = logging.getLogger('robj.test.testserver')

class RESTServer(HTTPServer):
    """
    Basic http server class that caches REST server state.
    """

    def __init__(self, *args, **kwargs):
        HTTPServer.__init__(self, *args, **kwargs)

        self.models = models
        self.data = DataStore()
        self.controllers = controllers

    @property
    def port(self):
        return self.server_address[1]

    def geturi(self, path=''):
        return 'http://localhost:%s%s' % (self.port, path)


class RESTRequestHandler(BaseHTTPRequestHandler):
    """
    Basic http server handler for dealing with our REST test environment
    for rObj.
    """

    debug = False
    server_version = 'REST/0.1'

    def log_exception(self, e):
        self.log_message('an exception has occured: %s', (e, ))

    def log_message(self, format, *args):
        if self.debug:
            log.info(format, *args)

    def log_error(self, format, *args):
        if self.debug:
            log.error(format, *args)

    def _handle_request(self):
        """
        Handle all types of supported methods.
        """

        try:
            # get the first available controller
            ControllerClass, pathVars = self.server.controllers.get(self.path)

            self.log_message('serving controller: %s' % ControllerClass.__name__)

            controller = ControllerClass(self.server.data, self,
                pathVars=pathVars)

            method = getattr(controller, 'do_%s' % self.command)
            response = method()

            if response.code >= 400:
                self.send_error(response.code, message=response.message)
                self.wfile.close()
                return

            self.send_response(response.code)
            self.send_header('Content-type', 'text/xml')
            self.send_header('Content-length', len(response.message))

            # write any headers specified by the response
            for key, val in response.iterheaders():
                self.send_header(key, val)

            self.end_headers()

            self.wfile.write(response.message)
            self.wfile.close()

        except Exception, e:
            self.log_exception(e)
            self.send_error(500, 'Internal server error: (%s)' % e)

    do_GET = do_PUT = do_POST = do_DELETE = _handle_request

    def do_HEAD(self):
        """
        Handle head requests.
        """

        self.send_error(501, 'Server does not support HEAD requests')


def StartServer(port=8080, fork=True, handlerClass=RESTRequestHandler,
    serverClass=RESTServer, debug=True):
    """
    Start a REST Server on the given port.
    """

    server_address = ('', port)

    handlerClass.debug = debug
    server = serverClass(server_address, handlerClass)

    sn = server.socket.getsockname()
    print 'starting server on %s port %s' % (sn[0], sn[1])

    if fork:
        pid = os.fork()
        if not pid:
            server.serve_forever()
        else:
            print 'started server process %s' % pid
    else:
        server.serve_forever()


def ThreadServer(port=8080, handlerClass=RESTRequestHandler,
    serverClass=RESTServer, debug=False):

    class Server(Thread, serverClass):
        def __init__(self, server_address, handlerClass):
            Thread.__init__(self)
            serverClass.__init__(self, server_address, handlerClass)

            self.setDaemon(True)

        def run(self):
            self.serve_forever()

    handlerClass.debug = debug

    server_address = ('', port)
    server = Server(server_address, handlerClass)

    sn = server.socket.getsockname()
    log.debug('starting server on %s port %s' % (sn[0], sn[1]))

    server.start()

    return server

if __name__ == '__main__':
    import sys
    from conary.lib import util

    sys.excepthook = util.genExcepthook()

    StartServer(fork=False)

    #server = ThreadServer()
    #import epdb; epdb.st()
