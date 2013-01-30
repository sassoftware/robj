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
            headers = HTTPHeaders()

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
        if isinstance(self.headers, HTTPHeaders):
            for k, v in self.headers.iteritems():
                yield k, v
        else:
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


class HTTPHeaders(object):
    """
    Case insensitive, case preserving, multi key dictionary like store for
    headers.
    """

    __slots__ = ('_headers', )

    class __Empty(object): pass

    def __init__(self, headers=None):
        self._headers = {}

        if headers:
            for key, value in headers.iteritems():
                self[key] = value

    def __iter__(self):
        return self._headers.__iter__()

    def iteritems(self):
        for key, hlst in sorted(self._headers.iteritems()):
            for header in hlst:
                yield header

    def __contains__(self, key):
        return key.lower() in self._headers

    def __setitem__(self, key, value):
        self.append(key, value, replace=False)

    def __getitem__(self, key):
        return self._headers.get(key.lower(), [])

    def __repr__(self):
        return repr([ x for x in self.iteritems() ])

    def append(self, name, value, replace=False):
        if replace:
            self.remove(name)
        self._headers.setdefault(name.lower(), []).append((name, value))

    def remove(self, name):
        self._headers.pop(name.lower(), None)

    def replace(self, name, value):
        self.append(name, value, replace=True)

    def copy(self):
        cls = self.__class__
        return cls(headers=self)

    def update(self, other):
        for key, value in other.iteritems():
            self.append(key, value)

    def get(self, key, default=__Empty):
        value = [ x[1] for x in self._headers.get(key.lower(), default) ]
        if value != default and isinstance(value, list) and len(value) == 1:
            return value[0]
        return value


def isHTTPData(obj):
    return isinstance(obj, HTTPData)
