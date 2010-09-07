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
from threading import Thread
from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from testserver.datastore import DataStore
from testserver.controllers import controllers

class RESTServer(HTTPServer):
    """
    Basic http server class that caches REST server state.
    """

    def __init__(self, *args, **kwargs):
        HTTPServer.__init__(self, *args, **kwargs)

        self.data = DataStore()
        self.controllers = controllers


class RESTRequestHandler(BaseHTTPRequestHandler):
    """
    Basic http server handler for dealing with our REST test environment
    for rObj.
    """

    server_version = 'REST/0.1'

    def log_exception(self, e):
        self.log_message('an exception has occured: %s', (e, ))

    def _handle_request(self):
        """
        Handle all types of supported methods.
        """

        try:
            # get the first available controller
            ControllerClass, pathVars = self.server.controllers.get(self.path)

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
    serverClass=RESTServer):
    """
    Start a REST Server on the given port.
    """

    server_address = ('', port)

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
    serverClass=RESTServer):

    class Server(Thread, serverClass):
        def __init__(self, server_address, handlerClass):
            Thread.__init__(self)
            serverClass.__init__(self, server_address, handlerClass)

            self.daemon = True

        def run(self):
            self.serve_forever()

    server_address = ('', port)
    server = Server(server_address, handlerClass)

    sn = server.socket.getsockname()
    print 'starting server on %s port %s' % (sn[0], sn[1])

    server.start()

    return server

if __name__ == '__main__':
    import sys
    from conary.lib import util

    sys.excepthook = util.genExcepthook()

    StartServer(fork=False)
