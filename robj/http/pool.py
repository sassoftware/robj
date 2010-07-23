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

log = logging.getLogger('robj.http.pool')

class ClientWorker(Thread):
    """
    Threaded HTTP client class.
    """

    _connectionClass = Connection

    def __init__(self, inq, maxConnections, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)
        self._inq = inq
        self._maxConnections = maxConnections

        self.daemon = True
        self._busy = False
        self._cache = {}

    @property
    def busy(self):
        return self._busy

    def _getConn(self, req):
        conn = self._cache.get(req.key, None)
        if conn is None:
            if len(self._cache) >= self._maxConnections:
                return None
            conn = self._connectionClass(*req.key)
            self._cache[req.key] = conn
        return conn

    def run(self):
        """
        Process client requests.
        """

        while True:
            log.info('%s: processing request' % self.name)

            # Get the next available request.
            req = self._inq.get()
            self._busy = True

            # Get a connection for the request.
            conn = self._getConn(req)

            # If the connection limit has been hit and we don't have a
            # connection for the request, put it back on the request queue.
            if conn is None:
                self._inq.put(req)

            # Handle the request.
            try:
                conn.request(req)
            except httplib.BadStatusLine:
                if req.retry():
                    log.info('retrying')
                    self._inq.put(req)
                else:
                    raise httplib.BadStatusLine

            self._busy = False

            # Wait a second before handling the next request.
            time.sleep(0.1)


class ConnectionManager(object):
    """
    Class for managing a pool of client workers.
    """

    _workerClass = ClientWorker

    def __init__(self, maxClients=None, maxConnections=None, threading=True):
        if maxClients is None:
            maxClients = 10
        if maxConnections is None:
            maxConnections = 2

        self._maxClients = maxClients
        self._maxConnections = maxConnections
        self._threading = threading

        self._reqs = Queue()

        self._workers = []

    def _createWorker(self):
        """
        Create worker if needed and maxClients has not been reached.
        """

        def addWorker():
            if len(self._workers) >= self._maxClients:
                return
            name = 'client-%s' % (len(self._workers) + 1)
            worker = self._workerClass(self._reqs, self._maxConnections,
                name=name)
            self._workers.append(worker)
            if self._threading:
                worker.start()

        # If there are already workers, look for an available worker.
        if self._workers:
            for worker in self._workers:
                if not worker.busy:
                    break
            else:
                addWorker()
        else:
            addWorker()

    def request(self, req):
        """
        Submit a request to the client pool.
        """

        self._createWorker()
        self._reqs.put(req)

        if not self._threading:
            worker = self._workers[0]
            worker.run()
