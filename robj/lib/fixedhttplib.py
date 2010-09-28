#
# This file contains a backported version of parts of httplib from python 2.6 to
# work with python 2.4. As such, it is licensed under the Python Software
# Foundation license agreement, which can be found at www.python.org.
#

import socket
import httplib
from array import array

__ALL__ = ('HTTPConnection', 'HTTPSConnection', )

class _Py26Send(object):
    """
    The _send_request and send methods were backported from python 2.6
    """

    def _send_request(self, method, url, body, headers):
        # honour explicitly requested Host: and Accept-Encoding headers
        header_names = dict.fromkeys([k.lower() for k in headers])
        skips = {}
        if 'host' in header_names:
            skips['skip_host'] = 1
        if 'accept-encoding' in header_names:
            skips['skip_accept_encoding'] = 1

        self.putrequest(method, url, **skips)

        if (body and ('content-length' not in header_names) and
            not 'transfer-encoding' in header_names):

            thelen=None
            try:
                thelen=str(len(body))
            except TypeError, te:  # pyflakes=ignore
                # If this is a file-like object, try to
                # fstat its file descriptor
                import os
                try:
                    thelen = str(os.fstat(body.fileno()).st_size)
                except (AttributeError, OSError):
                    # Don't send a length if this failed
                    if self.debuglevel > 0: print "Cannot stat!!"

            if thelen is not None:
                self.putheader('Content-Length',thelen)
        for hdr, value in headers.iteritems():
            self.putheader(hdr, value)
        self.endheaders()

        if body:
            self.send(body)

    def send(self, str):
        """Send `str' to the server."""
        if self.sock is None:
            if self.auto_open:
                self.connect()
            else:
                raise httplib.NotConnected()

        # send the data to the server. if we get a broken pipe, then close
        # the socket. we want to reconnect when somebody tries to send again.
        #
        # NOTE: we DO propagate the error, though, because we cannot simply
        #       ignore the error... the caller will know if they can retry.
        if self.debuglevel > 0:
            print "send:", repr(str)
        try:
            blocksize=8192
            if hasattr(str, 'read') and not isinstance(str, array):
                if self.debuglevel > 0: print "sendIng a read()able"
                data=str.read(blocksize)
                while data:
                    self.sock.sendall(data)
                    data=str.read(blocksize)
            elif hasattr(str, 'writeTo'):
                str.writeTo(self)
            else:
                self.sock.sendall(str)
        except socket.error, v:
            if v.args[0] == 32:      # Broken pipe
                self.close()
            raise


class HTTPConnection(_Py26Send, httplib.HTTPConnection):
    """
    HTTPConnection implementation that handles chunked encoding and sending
    file like objects.
    """

    def __init__(self, *args, **kwargs):
        _Py26Send.__init__(self)
        httplib.HTTPConnection.__init__(self, *args, **kwargs)


class HTTPSConnection(_Py26Send, httplib.HTTPSConnection):
    """
    HTTPSConnection implementation that handles chunked encoding and sending
    file like objects.
    """

    def __init__(self, *args, **kwargs):
        _Py26Send.__init__(self)
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)
