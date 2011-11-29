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
Module for miscellaneous utility functions.
"""

import os
import time
import types
import select
import tempfile

# This function is copied from conary.lib.util and tested as part of the
# conary testsuite.
def copyfileobj(source, dest, callback = None, digest = None,
                abortCheck = None, bufSize = 128*1024, rateLimit = None,
                sizeLimit = None, total=0):
    if hasattr(dest, 'send'):
        write = dest.send
    else:
        write = dest.write

    if rateLimit is None:
        rateLimit = 0

    if not rateLimit == 0:
        if rateLimit < 8 * 1024:
            bufSize = 4 * 1024
        else:
            bufSize = 8 * 1024

        rateLimit = float(rateLimit)

    starttime = time.time()

    copied = 0

    if abortCheck:
        pollObj = select.poll()
        pollObj.register(source.fileno(), select.POLLIN)
    else:
        pollObj = None

    while True:
        if sizeLimit and (sizeLimit - copied < bufSize):
            bufSize = sizeLimit - copied

        if abortCheck:
            # if we need to abortCheck, make sure we check it every time
            # read returns, and every five seconds
            l = []
            while not l:
                if abortCheck():
                    return None
                l = pollObj.poll(5000)

        buf = source.read(bufSize)
        if not buf:
            break

        total += len(buf)
        copied += len(buf)
        write(buf)

        if digest:
            digest.update(buf)

        now = time.time()
        if now == starttime:
            rate = 0 # don't bother limiting download until now > starttime.
        else:
            rate = copied / ((now - starttime))

        if callback:
            callback(total, rate)

        if copied == sizeLimit:
            break

        if rateLimit > 0 and rate > rateLimit:
            time.sleep((copied / rateLimit) - (copied / rate))

    return copied

def mktemp(suffix='', prefix='tmp', dir=None, unlink=True, mode='w+b'):
    fd, fname = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    fh = os.fdopen(fd, mode)
    if unlink:
        os.unlink(fname)
    return fh

def isXML(content):
    """
    Figure out if content is XML.
    @param content a string or file object (must be seekable)
    @type content str, unicode, or file 
    @rtype boolean
    """

    testStr = '<?xml'

    # File case.
    if hasattr(content, 'read') and hasattr(content, 'seek'):
        xml = content.read(len(testStr))
        content.seek(0)
        if testStr == xml:
            return True

    # String case.
    elif isinstance(content, types.StringTypes):
        if content.startswith(testStr):
            return True

    return False

def getContentType(content):
    """
    Figure out the content type of a given object.
    """

    xml = 'application/xml'

    if isXML(content):
        return xml
    elif content == '':
        return xml
    elif content is None:
        return xml
    else:
        return 'application/octet-stream'
