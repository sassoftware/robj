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
HTTP Request.
"""

import time
import logging

from robj.lib import util
from robj.errors import HTTPResponseTimeout

clog = logging.getLogger('robj.http.traffic')

class FLO(object):
    """
    File like object that logs the output of any write operations.
    """

    def __init__(self, f):
        self.f = f

    def fileno(self):
        return self.f.fileno()

    def read(self, size=-1):
        return self.f.read(size)

    def write(self, content):
        self.f.write(content)
        clog.debug(content)

    def seek(self, dist, start=0):
        self.f.seek(dist, start)

    def close(self):
        self.f.close()


class Response(object):
    """
    Simple HTTP Response wrapper class.
    """

    def __init__(self, resp):
        self.status = resp.status
        self.reason = resp.reason
        self.length = resp.length
        self.content = FLO(util.mktemp())
        self.headers = resp.getheaders()

        util.copyfileobj(resp, self.content)
        self.content.seek(0)

    def getheader(self, name):
        for header, value in self.headers:
            if name.lower() == header.lower():
                return value
        raise AttributeError, 'header not found: %s' % name


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
