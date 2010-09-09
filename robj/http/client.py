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

import base64
import urllib
import urlparse

from robj.http.request import Request
from robj.http.dispatcher import RequestDispatcher

class Client(object):
    """
    Basic REST HTTP client class.
    @param baseUri: URI for connectiong to the root of the desired web service.
                    This may contain user information and must be http or https.
    @type baseUri: str
    @param headers: Any heads that should be included in all requets.
    @type headers: dict
    @param maxClients: The maximum number of workers that will be created to
                       handle requets. Works are created as needed, rather than
                       being preallocated. (default: 10)
    @type maxClients: int
    @param maxConnections: The maximum number of connections each client thread
                           should cache. Client threads only cache one
                           connection per host. This should only matter if you
                           are talking to multiple hosts. (default: 2)
    @type maxConnections: int
    """

    def __init__(self, baseUri, headers=None, maxClients=None,
        maxConnections=None):

        self._headers = headers or dict()

        self._user = None
        self._passwd = None

        baseUri = baseUri.rstrip('/')
        self._scheme, loc, self._path, _, _ = urlparse.urlsplit(baseUri)

        userpass, self._hostport = urllib.splituser(loc)
        if userpass:
            self._user, self._passwd = urllib.splitpasswd(userpass)

        self._baseUri = urlparse.urlunsplit((self._scheme, self._hostport,
            self._path, None, None))

        if self._scheme not in ('http', 'https'):
            raise ValueError(self._scheme)

        self._dispatcher = RequestDispatcher(maxClients=maxClients,
            maxConnections=maxConnections)

    @property
    def baseURI(self):
        return self._baseUri

    def _getHeaders(self, headers=None):
        hdrs = self._headers.copy()
        hdrs.update(headers or {})
        if self._user is not None and self._passwd is not None:
            userpass = base64.b64encode('%s:%s' % (self._user, self._passwd))
            hdrs['Authorization'] = 'Basic %s' % userpass
        return hdrs

    def _request(self, method, uri, content=None):
        uri = uri.lstrip('/')
        path = '/'.join((self._path, uri))

        req = Request(method, path, self._scheme, self._hostport,
            content=content, headers=self._getHeaders())

        self._dispatcher.request(req)

        return req

    def do_GET(self, uri):
        return self._request('GET', uri)

    def do_POST(self, uri, content):
        return self._request('POST', uri, content=content)

    def do_PUT(self, uri, content):
        return self._request('PUT', uri, content=content)

    def do_DELETE(self, uri):
        return self._request('DELETE', uri)
