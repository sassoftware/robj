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
Basic REST HTTP client implementation.
"""

import os
import base64
import urllib
import urlparse

from robj.http.request import Request
from robj.http.pool import ConnectionManager

class Client(object):
    """
    Basic REST HTTP client class.
    """

    def __init__(self, baseUri, headers=None, maxClients=None,
        maxConnections=None):

        self._baseUri = baseUri
        self._headers = headers or dict()

        self._user = None
        self._passwd = None

        self._scheme, loc, self._path, _, _ = urlparse.urlsplit(self._baseUri)

        userpass, self._hostport = urllib.splituser(loc)
        if userpass:
            self._user, self._passwd = urllib.splitpasswd(userpass)

        if self._scheme not in ('http', 'https'):
            raise ValueError(self._scheme)

        self._mgr = ConnectionManager(maxClients=maxClients,
            maxConnections=maxConnections)

    @property
    def _getHeaders(self, headers=None):
        hdrs = self.headers.copy()
        hdrs.update(headers or {})
        if self._user is not None and self._passwd is not None:
            userpass = base64.b64encode('%s:%s' % (self._user, self._passwd))
            hdrs['Authorization'] = 'Basic %s' % userpass
        return hdrs

    def _request(self, method, uri, content=None):
        path = os.path.join(self._path, uri)

        req = Request(method, path, self._scheme, self._hostport,
            content=content, headers=self._getHeaders())

        self._mgr.request(req)

        return req

    def do_GET(self, uri):
        return self._request('GET', uri)

    def do_POST(self, uri, content):
        return self._request('POST', uri, content=content)

    def do_PUT(self, uri, content):
        return self._request('PUT', uri, content=content)

    def do_DELETE(self, uri):
        return self._request('DELETE', uri)
