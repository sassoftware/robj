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
Generic HTTP connection handling.
"""

import logging
import time

from robj.lib import fixedhttplib as httplib

clog = logging.getLogger('robj.http.traffic')
log = logging.getLogger('robj.http.connection')

class Connection(object):
    """
    Generic HTTP connection class.
    @param scheme: URI scheme, supports http or https.
    @type scheme: str
    @param hostport: Host and possibly port part of URI. (ex. localhost:8000)
    @type hostport str
    """

    _HTTPConnection = httplib.HTTPConnection
    _HTTPSConnection = httplib.HTTPSConnection

    _timeout = 15

    def __init__(self, scheme, hostport):
        self._scheme = scheme
        self._hostport = hostport

        self._conn = None
        self._last_used = 0

    def __hash__(self):
        return hash(self.key)

    def __cmp__(self, other):
        if not isinstance(other, self.__class__):
            return 1
        return cmp(self.key, other.key)

    @property
    def key(self):
        return (self._scheme, self._hostport)

    @property
    def _connection(self):
        if self._conn:
            return self._conn

        if self._scheme == 'http':
            cls = self._HTTPConnection
        else:
            cls = self._HTTPSConnection

        self._conn = cls(self._hostport)
        self._conn.connect()
        #self._conn.set_debuglevel(1)

        clog.debug('connected to %s://%s' % (self._scheme, self._hostport))

        return self._conn

    def _request(self, method, path, content=None, headers=None):
        clog.debug('CONNECTION(%s) SCHEME(%s) HOSTPORT(%s) METHOD(%s) PATH(%s)' %
            (id(self), self._scheme, self._hostport, method, path))
        if content and headers.get('Content-Type') == 'application/xml':
            clog.debug('CONNECTION(%s) CONTENT\n %s' % (id(self), content))
        clog.debug('CONNECTION(%s) HEADERS %s' % (id(self), headers))

        # If the content stream is a file like object that implements flush,
        # make sure the contents are flushed to disk. This is important to how
        # the underlying connection object dertermines file size.
        if hasattr(content, 'flush'):
            content.flush()

        # Also make sure to seek to the begining of the file stream.
        if hasattr(content, 'seek'):
            content.seek(0)

        # Check if the connection is stale before making the request in case we
        # are in single-threaded mode and aren't actively monitored.
        self.check()
        self._connection.request(method, path, body=content, headers=headers)
        response = self._connection.getresponse()
        self._last_used = time.time()
        return response

    def request(self, req):
        """
        Make the given request and post a response when ready.
        @param req: Request object.
        @type req: robj.http.request.Request
        """

        req.response = self._request(req.method, req.path, content=req.content,
            headers=req.headers)

    def close(self):
        """Close the connection immediately."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def check(self):
        """Close the connection if it has not been recently used."""
        if self._conn and time.time() - self._last_used > self._timeout:
            clog.debug('closing idle connection to %s://%s', self._scheme,
                    self._hostport)
            self._conn.close()
            self._conn = None
