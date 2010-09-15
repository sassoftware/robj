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

from robj.lib import util
from robj.errors import HTTPResponseTimeout

class Response(object):
    """
    Simple HTTP Response wrapper class.
    """

    def __init__(self, resp):
        self.status = resp.status
        self.reason = resp.reason
        self.length = resp.length
        self.content = util.mktemp()

        util.copyfileobj(resp, self.content)
        self.content.seek(0)


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

        self._response = None

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
    def retry(self):
        if self._retry > 0:
            self._retry -= 1
        return bool(self._retry)

    def _get_response(self):
        return self._response
    def _set_response(self, resp):
        if self._response is None:
            self._response = Response(resp)
    response = property(_get_response, _set_response)

    def wait(self, timeout=None):
        spent = 0
        delta = 0.1
        while not self.completed:
            time.sleep(delta)
            spent += delta
            if timeout and timeout <= spent:
                raise HTTPResponseTimeout
