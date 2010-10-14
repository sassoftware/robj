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

"""
Classes for manging pool of http clients.
"""

import time
import logging
import httplib
from Queue import Queue
from threading import Thread

from robj.http.connection import Connection

log = logging.getLogger('robj.http.dispatcher')

class RequestWorker(Thread):
    """
    Threaded HTTP client class.
    """

    _connectionClass = Connection

    def __init__(self, inq, maxConnections, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)
        self._inq = inq
        self._maxConnections = maxConnections

        self.daemon = True

        self._cache = {}
        self._busy = False

    @property
    def busy(self):
        return self._busy

    def _getConn(self, req):
        conn = self._cache.get(req.key, None)
        if conn is None and len(self._cache) < self._maxConnections:
            conn = self._connectionClass(*req.key)
            self._cache[req.key] = conn
        return conn

    def run(self):
        """
        Process client requests forever.
        """

        while True:
            # Get the next available request.
            req = self._inq.get()
            self._busy = True
            req = self.handleRequest(req)
            if req is not None:
                self._inq.put(req)
            self._busy = False

    def handleRequest(self, req):
        """
        Process one client request.
        """

        log.debug('%s: processing request' % self.getName())

        # Get a connection for the request.
        conn = self._getConn(req)

        # If the connection limit has been hit and we don't have a
        # connection for the request, put it back on the request queue.
        if conn is None:
            log.error('%s: no connection found for request' % self.getName())
            return req

        # Handle the request.
        try:
            try:
                conn.request(req)
            except httplib.BadStatusLine:
                if req.retry:
                    log.warn('%s: retrying' % self.getName())
                    return req
                else:
                    raise
        except Exception, e:  # pyflakes=ignore
            # Remove the connection object from the local cache since it is
            # now in an error state and thus unusable.
            self._cache.pop(req.key)
            raise

        # Wait a tenth of a second before handling the next request.
        time.sleep(0.1)


class RequestDispatcher(object):
    """
    Dispatch requests to a pool of HTTP clients.
    @param maxClients: The maximum number of workers that will be created to
                       handle requets. Works are created as needed, rather than
                       being preallocated. (default: 1)
    @type maxClients: int
    @param maxConnections: The maximum number of connections each client thread
                           should cache. Client threads only cache one
                           connection per host. This should only matter if you
                           are talking to multiple hosts. (default: 2)
    @type maxConnections: int
    """

    _workerClass = RequestWorker

    def __init__(self, maxClients=None, maxConnections=None):
        if maxClients is None:
            maxClients = 1
        if maxConnections is None:
            maxConnections = 2

        self._maxClients = maxClients
        self._maxConnections = maxConnections

        self._reqs = Queue()
        self._workers = []

    def _createWorker(self):
        """
        Create worker if needed and maxClients has not been reached.
        """

        # Don't create any more workers if the client limit has already
        # been reached.
        if len(self._workers) >= self._maxClients:
            return

        # Check for availble workers before allocating a new instance.
        for worker in self._workers:
            if not worker.busy:
                break

        # If no available workers were found, allocate a new instance.
        else:
            name = 'client-%s' % len(self._workers)
            worker = self._workerClass(self._reqs, self._maxConnections,
                name=name)
            self._workers.append(worker)
            worker.start()

    def request(self, req):
        """
        Submit a request to the client pool.
        """

        self._reqs.put(req)

        # Don't use threading if there is only one client allowed.
        if self._maxClients > 1:
            self._createWorker()
        else:
            if not self._workers:
                self._workers.append(self._workerClass(self._reqs,
                    self._maxConnections, name='client'))
            while self._workers[0].handleRequest(req):
                self._workers[0].handleRequest(req)
