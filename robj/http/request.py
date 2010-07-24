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
HTTP Request.
"""

import time

from robj.errors import HTTPResponseTimeout

class Response(object):
    """
    Simple HTTP Response wrapper class.
    """

    def __init__(self, resp):
        self.status = resp.status
        self.reason = resp.reason
        self.length = resp.length
        self._doc = resp.read()

    def read(self):
        return self._doc


class Request(object):
    """
    Simple HTTP Request class.
    """

    def __init__(self, method, path, scheme, hostport, content=None,
        headers=None):

        self.method = method
        self.path = path
        self.content = content
        self.headers = headers

        self._scheme = scheme
        self._hostport = hostport

        self._retry = 10

        self.response = None

    def __hash__(self):
        return hash(self.key)

    def __cmp__(self, other):
        if not isinstance(other, self.__class__):
            return 1
        return cmp(self.key, other.key)

    @property
    def key(self):
        return (self._scheme, self._hostport)

    @property
    def completed(self):
        return self.response is not None

    @property
    def resp(self):
        return self.response

    def retry(self):
        self._retry -= 1
        return self._retry

    def setResponse(self, resp):
        self.response = Response(resp)

    def wait(self, timeout=None):
        spent = 0
        delta = 0.1
        while not self.completed:
            time.sleep(delta)
            spent += delta
            if timeout and timeout <= spent:
                raise HTTPResponseTimeout
