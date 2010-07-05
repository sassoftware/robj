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
Module for binding the HTTP client layer to xobj.
"""

import urllib
import urlparse
from threading import RLock

from xobj import xobj

from robj.obj import rObj
from robj.errors import ExternalUriError
from robj.http import HTTPClient as _HTTPClient

def cache(func):
    def wrapper(self, *args, **kwargs):
        resp = func(self, *args, **kwargs)
        uri = args[0]
        robj = self._instCache.cache(self, uri, resp)
        return robj
    return wrapper


class HTTPClient(object):
    """
    Wrapper around the basic http client that integrates xobj.
    """

    def __init__(self, baseUri, headers=None, maxClients=None,
        maxConnections=None):
        self._baseUri = baseUri
        self._headers = headers
        self._maxClients = maxClients
        self._maxConnections = maxConnections

        self._client = _HTTPClient(self._baseUri, headers=self._headers,
            maxClients=self._maxClients, maxConnections=self._maxConnections)

        self._instCache = InstanceCache()

    def _resolve(self, uri):
        """
        Make sure uri is based at the baseUri and shorten to be appened on the
        baseUri.
        """

        if uri.startswith('http'):
            scheme, loc, path, _, _ = urlparse.urlsplit(self._baseUri)
            userpass, hostport = urllib.splituser(loc)
            base = urlparse.urlunsplit((scheme, loc, path, None, None))
            if uri.startswith(base):
                return uri[len(base)-1:]
            else:
                raise ExternalUriError(uri=uri, base=base)

        return uri

    @cache
    def do_POST(self, uri, xdoc):
        xml = xobj.toxml(xdoc)

        uri = self._resolve(uri)
        req = self._client.do_POST(uri, xml)
        req.wait()

        xml2 = req.resp.read()
        doc = xobj.parse(xml2)

        req.resp.doc = doc
        return req.resp

    @cache
    def do_PUT(self, uri, xdoc):
        xml = xobj.toxml(xdoc)

        uri = self._resolve(uri)
        req = self._client.do_PUT(uri, xml)
        req.wait()

        xml2 = req.resp.read()
        doc = xobj.parse(xml2)

        req.resp.doc = doc
        return req.resp

    @cache
    def do_GET(self, uri):
        uri = self._resolve(uri)
        req = self._client.do_GET(uri)
        req.wait()

        xml = req.resp.read()
        doc = xobj.parse(xml)

        req.resp.doc = doc
        return req.resp

    @cache
    def do_DELETE(self, uri):
        uri = self._resolve(uri)
        req = self._client.do_DELETE(uri)
        req.wait()

        req.resp.doc = None
        return req.resp


class InstanceCache(dict):
    """
    Cache of all URIs and associated objects.
    """

    def __init__(self):
        dict.__init__(self)
        self._writeLock = RLock()

    def clear(self):
        """
        Clear the cache of rObj instances. This will result in orphaned
        instances in memory.
        """

        self._writeLock.acquire()
        for element in self:
            self.pop(element)
        self._writeLock.release()

    def cache(self, client, uri, resp):
        """
        Cache the given robj if needed.
        """

        self._writeLock.acquire()

        if uri in self:
            robj = self[uri]
            if not robj._dirty:
                robj._doc = resp.doc
        else:
            robj = rObj(uri, client, doc=resp.doc)
            self[uri] = robj

        self._writeLock.release()
        return robj
