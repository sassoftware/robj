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

from threading import RLock

from xobj import xobj

from robj.proxy import rObjProxy
from robj.errors import HTTPDeleteError
from robj.errors import ExternalUriError
from robj.errors import SerializationError
from robj.http import HTTPClient as _HTTPClient

__ALL__ = ('HTTPClient', )

class HTTPClient(object):
    """
    Wrapper around the basic http client that integrates xobj.
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

        self._client = _HTTPClient(baseUri, headers=headers,
            maxClients=maxClients, maxConnections=maxConnections)

        self._instCache = InstanceCache()

    def _normalize_uri(self, uri):
        """
        Make sure uri is based at the baseUri and shorten to be appened on the
        baseUri.
        """

        # Strip off trailing slashes
        uri = uri.rstrip('/')

        # Assume the URI is relative if it doesn't start with an
        # expected scheme.
        if not uri.startswith('http'):
            return uri

        # Strip off the leading base URI.
        elif uri.startswith(self._client.baseURI):
            return uri[len(self._client.baseURI):]

        # Otherwise, raise an exception.
        else:
            raise ExternalUriError(uri=uri, base=self._client.baseURI)

    def _serialize_document(self, doc):
        """
        Serialize a object tree into xml.
        """

        # Serialize document to xml.
        if isinstance(doc, xobj.Document):
            xml = doc.toxml()
        else:
            meta = getattr(doc, '_xobj', None)

            # Raise an exception if we can't figure out the tag.
            if meta is None or not meta.tag:
                raise SerializationError(instance=doc,
                    msg=('Can not determine tag'))

            xml = xobj.toxml(doc, meta.tag)

        return xml

    def _handle_request(self, method, uri, xdoc=None, parent=None):
        """
        Process all types of requests.
        """

        # Normalize the URI.
        uri = self._normalize_uri(uri)

        # Check the cache before moving on if this is a GET.
        if method == 'GET' and uri in self._instCache:
            return self._instCache[uri]

        if method in ('POST', 'PUT', ):
            # Make sure there is a document for PUT and POST requests.
            if not xdoc:
                raise AttributeError, 'method requires document instance'

            xml = self._serialize_document(xdoc)
            args = (uri, xml)
        else:
            args = (uri, )

        # Call client method
        func = getattr(self._client, 'do_%s' % method)
        request = func(*args)

        # Wait for request to complete.
        request.wait()

        # Get the response
        response = request.response

        # Special case DELETE method.
        if method == 'DELETE':
            # Raise an exception if the resource could not be deleted.
            if response.status not in (404, 200):
                raise HTTPDeleteError(uri=self._uri, status=response.status,
                    reason=response.reason, response=response)

            self._instCache.clear(uri)

            return response

        # Parse XML document.
        doc = xobj.parse(response.read())

        # Cache response and return rObjProxy instance.
        return self._instCache.cache(self, uri, doc, parent=parent)

    def do_GET(self, *args, **kwargs):
        """
        Process GET requests.
        @param uri: Full or partial URI (relative to the base URI).
        @type uri: str
        @return rObj representing response.
        @rtype robj.obj.rObjProxy
        """

        return self._handle_request('GET', *args, **kwargs)

    def do_POST(self, *args, **kwargs):
        """
        Process POST requests.
        @param uri: Full or partial URI (relative to the base URI).
        @type uri: str
        @param xdoc: A serializable instance that may include a xobj document
                     wrapper.
        @type xdoc: instance
        @return rObj representing response.
        @rtype robj.obj.rObjProxy
        """

        return self._handle_request('POST', *args, **kwargs)

    def do_PUT(self, *args, **kwargs):
        """
        Process PUT requests.
        @param uri: Full or partial URI (relative to the base URI).
        @type uri: str
        @param xdoc: A serializable instance that may include a xobj document
                     wrapper.
        @type xdoc: instance
        @return rObj representing response.
        @rtype robj.obj.rObjProxy
        """

        return self._handle_request('PUT', *args, **kwargs)

    def do_DELETE(self, *args, **kwargs):
        """
        Process DELETE requests.
        @param uri: Full or partial URI (relative to the base URI).
        @type uri: str
        @return response object
        @rtype robj.http.request.Response
        """

        return self._handle_request('DELETE', *args, **kwargs)


class InstanceCache(dict):
    """
    Cache of all URIs and associated objects.
    """

    def __init__(self):
        dict.__init__(self)
        self._write_lock = RLock()

    def clear(self, uri=None):
        """
        Clear the cache of rObj instances. This will result in orphaned
        instances in memory.
        """

        self._write_lock.acquire()
        if uri:
            self.pop(uri, None)
        else:
            for element in self:
                self.pop(element)
        self._write_lock.release()

    def cache(self, client, uri, doc, parent=None):
        """
        Cache the given robj if needed.
        """

        self._write_lock.acquire()

        # Pull the top level object out of the document.
        if isinstance(doc, xobj.Document):
            assert len(doc._xobj.elements) == 1
            doc = getattr(doc, doc._xobj.elements[0])

        if uri in self:
            robj = self[uri]
            if not robj._dirty:
                robj._doc = doc
        else:
            robj = rObjProxy(uri, client, doc, parent=parent)
            self[uri] = robj

        self._write_lock.release()
        return robj
