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

import types
from threading import RLock

from xobj import xobj

from robj import errors
from robj.lib import util
from robj.lib import httputil
from robj.proxy import rObjProxy
from robj.http import HTTPClient as _HTTPClient

from robj.errors import HTTPDeleteError
from robj.errors import ExternalUriError
from robj.errors import SerializationError
from robj.errors import HTTPMaxRedirectReachedError

__all__ = ('HTTPClient', )


class HTTPClient(object):
    """
    Wrapper around the basic http client that integrates xobj.
    @param baseUri: URI for connectiong to the root of the desired web service.
                    This may contain user information and must be http or https.
    @type baseUri: str
    @param headers: Any headers that should be included in all requets.
    @type headers: dict
    @param maxClients: The maximum number of workers that will be created to
                       handle requets. Works are created as needed, rather than
                       being preallocated. (default: 1)
    @type maxClients: int
    @param maxConnections: The maximum number of connections each client thread
                           should cache. Client threads only cache one
                           connection per host. This should only matter if you
                           are talking to multiple hosts. (default: 2)
    @type maxConnections: int
    @param maxRedirects: The maximum number of redirects that will be followed
                         before an exception is raised. (default: 10)
    @type maxRedirects: int
    """

    error_exceptions = {
        300: errors.HTTPUnhandledRedirectError,
        305: errors.HTTPUnhandledRedirectError,
        306: errors.HTTPUnhandledRedirectError,

        401: errors.HTTPUnauthorizedError,
        403: errors.HTTPForbiddenError,
        404: errors.HTTPNotFoundError,
        405: errors.HTTPMethodNotAllowedError,
        406: errors.HTTPNotAcceptableError,
        408: errors.HTTPRequestTimeoutError,
        409: errors.HTTPConflictError,
        410: errors.HTTPGoneError,
        500: errors.HTTPInternalServerError,
        501: errors.HTTPNotImplementedError,
        502: errors.HTTPBadGatewayError,
        503: errors.HTTPServiceUnavailableError,
        504: errors.HTTPGatewayTimeoutError,
    }

    def __init__(self, baseUri, headers=None, maxClients=None,
        maxConnections=None, maxRedirects=None):

        if maxRedirects is None:
            maxRedirects = 10
        self._maxRedirects = maxRedirects

        self._client = _HTTPClient(baseUri, headers=headers,
            maxClients=maxClients, maxConnections=maxConnections)

        self.cache = InstanceCache()
        self._redirects = {}

    def _normalize_uri(self, uri):
        """
        Make sure uri is based at the baseUri and shorten to be appened on the
        baseUri.
        """

        # Strip off trailing slashes
        uri = uri.rstrip('/')

        # Trim off the base path.
        if uri.startswith(self._client.path):
            return uri[len(self._client.path):].rstrip('/')

        # Assume the URI is relative if it doesn't start with an
        # expected scheme.
        elif not uri.startswith('http'):
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

            # If this is not an xobj and it is a string, but it doesn't look
            # like an xml document or doc is a file object, assume that the
            # client meant to upload this document to the server.
            if (meta is None and (isinstance(doc, file) or
                (isinstance(doc, types.StringTypes) and
                 not util.isXML(doc)) or httputil.isHTTPData(doc))):
                return doc

            # Raise an exception if we can't figure out the tag.
            if meta is None or not meta.tag:
                raise SerializationError(instance=doc,
                    msg='Can not determine tag')

            xml = xobj.toxml(doc, meta.tag)

        return xml

    def _handle_error(self, uri, request, response):
        """
        Handle all error conditions by raising a reasonable exception.
        """

        default = errors.HTTPResponseError
        ExceptionClass = self.error_exceptions.get(response.status, default)

        # If error code is not marked as ignored, raise the definied exception.
        if ExceptionClass is not None:
            raise ExceptionClass(uri=uri, status=response.status,
                reason=response.reason, response=response)

        # If this error status is marked to be ignored, just return the
        # response.
        return response

    def _handle_redirect(self, uri, request, response, parent=None,
        redirectCount=0):
        """
        Handle all redirect conditions. This may include long running jobs
        implemented through a see other (303).
        """

        def handle_request(location, method=None, cache=True):
            return self._handle_request(method, location,
                xdoc=request.content, parent=parent, cache=cache,
                redirectCount=redirectCount+1)

        # Raise an exception for any redirect types that are not currently
        # handled by this method.
        if response.status in self.error_exceptions:
            error = self.error_exceptions[response.status]
            raise error(uri=uri, status=response.status, reason=response.reason,
                response=response)

        if redirectCount >= self._maxRedirects:
            raise HTTPMaxRedirectReachedError(uri=uri, status=response.status,
                reason=response.reason, response=response)

        # Everything from here should have a location header set.
        location = response.getheader('location')

        # 301: Moved Permanently - Resource has moved permanently and it is
        # considered safe to cache both the redirect and result.
        if response.status == 301:
            self._redirects[uri] = self._normalize_uri(location)
            return handle_request(location, method=request.method, cache=True)

        # 302: Found - not cachable
        elif response.status == 302:
            obj = handle_request(location, method='GET', cache=True)
            obj._uri = uri
            return obj

        # 303: See Other - redirect not cacheable, redirected resource cachable.
        elif response.status == 303:
            return handle_request(location, method='GET', cache=True)

        # 304: Not Modified - resource has not changed since the last request,
        # returned cached instance of location.
        elif response.status == 304:
            location = self._normalize_uri(location)
            if location in self.cache:
                return self.cache[location]
            else:
                obj = handle_request(location, method=request.method,
                    cache=True)
                obj._uri = uri
                return obj

        # 307: Temporary Redirect - not cachable
        elif response.status == 307:
            obj = handle_request(location, method=request.method, cache=False)
            obj._uri = uri
            return obj

        # Everything else must be an error
        else:
            raise errors.HTTPUnknownRedirect(uri=uri, status=response.status,
                reason=response.reason, response=response)

    def _handle_request(self, method, uri, xdoc=None, parent=None, cache=True,
        redirectCount=0):
        """
        Process all types of requests.
        """

        # Normalize the URI.
        uri = self._normalize_uri(uri)

        # Check if this is a permanent redirect
        uri = self._redirects.get(uri, uri)

        # Check the cache before moving on if this is a GET.
        if method == 'GET' and uri in self.cache and cache:
            return self.cache[uri]

        xml = None
        rawdoc = False
        if method in ('POST', 'PUT', ):
            # Make sure there is a document for PUT and POST requests.
            if xdoc is None:
                raise TypeError, 'method requires document instance'

            xml = self._serialize_document(xdoc)
            if xml == xdoc:
                rawdoc = True
            args = (uri, xml)
        else:
            args = (uri, )

        # Allow custom http data to override method.
        if xml and httputil.isHTTPData(xml) and xml.method:
            method = xml.method

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
                raise HTTPDeleteError(uri=uri, status=response.status,
                    reason=response.reason, response=response)

            self.cache.clear(uri)

            return response

        # Handle other error codes.
        if response.status >= 400:
            return self._handle_error(uri, request, response)

        # Handle redirects.
        elif response.status >= 300:
            return self._handle_redirect(uri, request, response, parent=parent,
                redirectCount=redirectCount)

        # If the raw document was sent to the server, this is probably a file
        # upload and the response should not contain an xml document.
        if rawdoc:
            return response

        # Make sure the response looks like valid xml, otherwise assume that
        # this is a file download an return the content of the response.
        content = response.content
        if not util.isXML(content):
            return content

        # Parse XML document.
        doc = xobj.parsef(content)
        content.close()

        # Pull the top level object out of the document.
        assert isinstance(doc, xobj.Document)
        assert len(doc._xobj.elements) == 1
        root = getattr(doc, doc._xobj.elements[0])

        # If the top level object has an 'id' attribute, use that as its URI.
        # This is here to handle appending to collections, where the resource
        # you get back is the new instance, not the collection itself.
        if method != 'GET' and 'id' in root._xobj.attributes:
            uri = self._normalize_uri(root.id)

        # Cache response and return rObjProxy instance.
        return self.cache(self, uri, root, parent=parent, cache=cache)

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
            dict.clear(self)
        self._write_lock.release()

    def cache(self, client, uri, root, parent=None, cache=True):
        """
        Cache the given robj if needed.
        """

        # Make sure that all cached URIs are normalized.
        uri = client._normalize_uri(uri)

        self._write_lock.acquire()

        if uri in self:
            robj = self[uri]
            if not robj._dirty:
                robj._root = root
                robj._reset()
        else:
            robj = rObjProxy(uri, client, root, parent=parent)
            if cache:
                self[uri] = robj

        self._write_lock.release()
        return robj

    __call__ = cache
