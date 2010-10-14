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
Module for httplib customizations.
"""

from robj.lib import util
from robj.lib import xutil

class HTTPData(object):
    __slots__ = ('data', 'method', 'size', 'headers', 'contentType', 'callback',
        'chunked', 'bufferSize', 'rateLimit', 'tag')

    CHUNK_SIZE = 262144
    BUFFER_SIZE = 8192

    def __init__(self, data=None, method=None, size=None, headers=None,
        contentType=None, callback=None, chunked=None, bufferSize=None,
        rateLimit=None, tag=None):

        if headers is None:
            headers = {}

        if data is not None:
            if isinstance(data, dict):
                obj = xutil.XObjify(data, tag)
                data = xutil.xobj.toxml(obj, tag)

            if hasattr(data, 'read'):
                if chunked:
                    headers['Transfer-Encoding'] = 'Chunked'
            else:
                data = data.encode('utf-8')
                size = len(data)

        if contentType is None:
            contentType = util.getContentType(data)

        self.method = method
        self.data = data
        self.headers = headers
        self.size = size
        self.contentType = contentType
        self.callback = callback
        self.chunked = chunked
        self.bufferSize = bufferSize or self.BUFFER_SIZE
        self.rateLimit = rateLimit

    def iterheaders(self):
        for k, v in sorted(self.headers.iteritems()):
            yield k, str(v)
        if self.size is not None:
            yield 'Content-Length', str(self.size)
        if self.contentType is not None:
            yield 'Content-Type', self.contentType

    def writeTo(self, connection):
        if self.data is None:
            return

        if not hasattr(self.data, 'read'):
            connection.send(self.data)
            return

        if self.chunked:
            # Use chunked coding
            output = ChunkedSender(connection)
            util.copyfileobj(self.data, output, bufSize=self.bufferSize,
                    callback=self.callback, rateLimit=self.rateLimit)
            output.close()
        elif self.size is not None:
            # Use identity coding
            util.copyfileobj(self.data, connection, bufSize=self.bufferSize,
                callback=self.callback, rateLimit=self.rateLimit,
                sizeLimit=self.size)
        else:
            raise RuntimeError("Request must use chunked transfer coding "
                    "if size is not known.")


class ChunkedSender(object):
    """
    Do HTTP chunked transfer coding by wrapping a socket-like object,
    intercepting send() calls and sending the correct leading and trailing
    metadata.
    """

    def __init__(self, target):
        self.target = target

    def send(self, data):
        self.target.send("%x\r\n%s\r\n" % (len(data), data))

    def close(self, trailer=''):
        self.target.send("0\r\n%s\r\n" % (trailer,))


def isHTTPData(obj):
    return isinstance(obj, HTTPData)
