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

class HTTPData(object):
    __slots__ = ('data', 'method', 'size', 'headers', 'contentType', 'callback',
        'chunked', 'bufferSize', 'rateLimit', )

    CHUNK_SIZE = 262144
    BUFFER_SIZE = 8192

    def __init__(self, data=None, method=None, size=None, headers=None,
        contentType=None, callback=None, chunked=None, bufferSize=None,
        rateLimit=None):

        if headers is None:
            headers = {}

        if data is not None:
            if hasattr(data, 'read'):
                if chunked:
                    headers['Transfer-Encoding'] = 'Chunked'
            else:
                data = data.encode('utf-8')
                size = len(data)

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

        if not self.chunked:
            util.copyfileobj(self.data, connection, bufSize=self.bufferSize,
                callback=self.callback, rateLimit=self.rateLimit,
                sizeLimit=self.size)
            return

        assert self.size is not None

        # keep track of the total amount of data sent so that the
        # callback passed in to copyfileobj can report progress correctly
        sent = 0
        chunk = self.CHUNK_SIZE
        while self.size - sent:
            if chunk > self.size - sent:
                chunk = self.size - sent

            # first send the hex-encoded size
            connection.send('%x\r\n' % chunk)

            # then the chunk of data
            util.copyfileobj(self.data, connection, bufSize=chunk,
                callback=self.callback, rateLimit=self.rateLimit,
                sizeLimit=chunk, total=sent)

            # send \r\n after the chunked data
            connection.send("\r\n")

            sent += chunk
        # terminate the chunked encoding
        connection.send('0\r\n\r\n')


def isHTTPData(obj):
    return isinstance(obj, HTTPData)
