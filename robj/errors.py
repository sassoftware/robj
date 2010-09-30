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

class rObjError(Exception):
    """
    Base rObj Error for all other errors to inherit from.
    """

    _params = []
    _template = 'An unknown error has occured.'

    def __init__(self, **kwargs):
        Exception.__init__(self)

        self._kwargs = kwargs

        # Copy kwargs to attributes
        for key in self._params:
           setattr(self, key, kwargs[key])

    def __str__(self):
        return self._template % self.__dict__

    def __repr__(self):
        params = ', '.join('%s=%r' % x for x in self._kwargs.iteritems())
        return '%s(%s)' % (self.__class__, params)


class ObjError(rObjError):
    """
    Generic Object layer error.
    """


class RemoteInstanceOverwriteError(ObjError, AttributeError):
    """
    Raised when someone tries to set an attribute that has already been set
    that has an id attribute.
    """

    _params = ['uri', 'id', 'name', ]
    _templates = ('Can not override an attribute, %(name)s, of %(uri)s that is '
        'represented by an instance on the server at %(id)s.')


class HTTPError(rObjError):
    """
    Generic HTTP layer error.
    """


class HTTPResponseTimeout(HTTPError):
    """
    Raised when request.wait is called with a timeout and that timeout has been
    reached.
    """

    _params = []
    _template = 'Timeout reached waiting for response'


class HTTPResponseError(HTTPError):
    """
    Generic response error.
    """

    _params = ['uri', 'status', 'reason', 'response', ]
    _template = 'Response error accessing %(uri)s: %(reason)s [%(status)s]'


class HTTPDeleteError(HTTPResponseError):
    """
    Raised when an unexpected status is returned from a DELETE request.
    """

    _template = 'Deleting %(uri)s failed with %(reason)s [%(status)s]'


class HTTPUnauthorizedError(HTTPResponseError):
    """
    Raised when a 401 status is returned.
    """


class HTTPForbiddenError(HTTPResponseError):
    """
    Raised when a 403 status is returned.
    """


class HTTPNotFoundError(HTTPResponseError):
    """
    Raised when a 404 status is returned.
    """


class HTTPMethodNotAllowedError(HTTPResponseError):
    """
    Raised when a 405 status is returned.
    """


class HTTPNotAcceptableError(HTTPResponseError):
    """
    Raised when a 406 status is returned.
    """


class HTTPRequestTimeoutError(HTTPResponseError):
    """
    Raised when a 408 status is returned.
    """


class HTTPConflictError(HTTPResponseError):
    """
    Raised when a 409 status is returned.
    """


class HTTPGoneError(HTTPResponseError):
    """
    Raised when a 410 status is returned.
    """


class HTTPInternalServerError(HTTPResponseError):
    """
    Raised when a 500 status is returned.
    """


class HTTPNotImplementedError(HTTPResponseError):
    """
    Raised when a 501 status is returned.
    """


class HTTPBadGatewayError(HTTPResponseError):
    """
    Raised when a 502 status is returned.
    """


class HTTPServiceUnavailableError(HTTPResponseError):
    """
    Raised when a 503 status is returned.
    """


class HTTPGatewayTimeoutError(HTTPResponseError):
    """
    Raised when a 504 status is returned.
    """


class HTTPRedirectError(HTTPError):
    """
    Generic redirect error.
    """

    _params = ['uri', 'status', 'reason', 'response', ]
    _template = ('Error processing redirect: uri=%(uri)s, status=%(status)s, '
        'reason=%(reason)s')


class HTTPUnhandledRedirectError(HTTPRedirectError):
    """
    Raised when a redirect status code is returned that rObj doesn't know how to
    deal with.
    """

class HTTPUnknownRedirectStatusError(HTTPRedirectError):
    """
    Raised if the server returns a status code in the 300s that isn't otherwise
    handled.
    """

class HTTPMaxRedirectReachedError(HTTPRedirectError):
    """
    Raised if the maximum number of redirects is reached or a loop is dicovered.
    """


class GlueError(rObjError):
    """
    Generic glue layer error.
    """


class ExternalUriError(GlueError):
    """
    Raised when a uri is accessed that is at a different base than the original 
    uri.
    """

    _params = ['uri', 'base', ]
    _template = ('Can not access %(uri)s since it is not under the base uri '
        '%(base)s')


class SerializationError(GlueError):
    """
    Raised when an instance can not be serialized via XObj.
    """

    _params = ['instance', 'msg', ]
    _template = 'Unable to serialize instance: %(msg)s'
