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


"""
Basic REST HTTP client implementation.
"""

import base64
import urllib
import urlparse

from robj.lib import util
from robj.lib.httputil import HTTPHeaders

from robj.http.request import Request
from robj.http.dispatcher import RequestDispatcher

class Client(object):
    """
    Basic REST HTTP client class.
    @param baseUri: URI for connectiong to the root of the desired web service.
                    This may contain user information and must be http or https.
    @type baseUri: str
    @param headers: Any headers that should be included in all requets.
    @type headers: dict like object
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

    def __init__(self, baseUri, headers=None, maxClients=None,
        maxConnections=None):

        self._headers = headers or HTTPHeaders()

        self._user = None
        self._passwd = None

        baseUri = baseUri.rstrip('/')
        self._scheme, loc, self._path, query, frag = urlparse.urlsplit(baseUri)

        userpass, self._hostport = urllib.splituser(loc)
        if userpass:
            self._user, self._passwd = urllib.splitpasswd(userpass)

        self._baseUri = urlparse.urlunsplit((self._scheme, self._hostport,
            self._path, None, None))

        if self._scheme not in ('http', 'https'):
            raise ValueError(self._scheme)

        self._dispatcher = RequestDispatcher(maxClients=maxClients,
            maxConnections=maxConnections)

        self._queryFragment = urlparse.urlunsplit(('', '', '', query, frag))

    @property
    def baseURI(self):
        return self._baseUri

    @property
    def queryFragment(self):
        return self._queryFragment

    @property
    def path(self):
        return self._path.rstrip('/')

    def _getHost(self):
        if ':' in self._hostport:
            host, port = self._hostport.split(':')
            if ((self._scheme.lower() == 'http' and port == 80) or
                (self._scheme.lower() == 'https' and port == 443)):
                return host

        return self._hostport

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

        headers = self._getHeaders({
            'Content-Type': util.getContentType(content),
            'Host': self._getHost().encode('idna'),
        })

        # If the content object defines a iterheaders method, as
        # httputil.HTTPData does, allow the content headers to override any
        # other headers. NOTE: The content object must define its own content
        # type if you want something other than application/octet-stream.
        if hasattr(content, 'iterheaders'):
            for key, val in content.iterheaders():
                headers.replace(key, val)

        req = Request(method, path, self._scheme, self._hostport,
            content=content, headers=headers)

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
