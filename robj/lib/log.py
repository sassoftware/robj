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
Module for setting up logging.
"""

import sys
import logging
import tempfile
from logging import handlers

def _setupHandlers(logFile=None, prefix=None):
    """
    Create log handlers.
    """

    if not prefix:
        prefix = 'robj-log-'

    logSize = 1024 * 1024 * 50
    logFile = logFile and logFile or tempfile.mktemp(prefix=prefix)

    streamHandler = logging.StreamHandler(sys.stdout)
    logFileHandler = handlers.RotatingFileHandler(logFile,
                                                  maxBytes=logSize,
                                                  backupCount=5)

    streamFormatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fileFormatter = logging.Formatter('%(asctime)s %(levelname)s '
        '%(name)s %(message)s')

    streamHandler.setFormatter(streamFormatter)
    logFileHandler.setFormatter(fileFormatter)

    return (streamHandler, logFileHandler)

def setupLogging(logFile=None):
    """
    Setup the root logger that should be inherited by all other loggers.
    """

    # Setup root logger
    rootHandlers = _setupHandlers(logFile=logFile, prefix='robj-')

    rootLog = logging.getLogger('')
    for handler in rootHandlers:
        rootLog.addHandler(handler)
    rootLog.setLevel(logging.INFO)

    # Setup connection logger
    connLogFile = logFile
    if logFile:
        connLogFile = logFile + '-connections'

    connHandlers = _setupHandlers(logFile=connLogFile,
                                  prefix='robj-connections-')

    connLog = logging.getLogger('robj.http.traffic')
    for handler in connLog.handlers:
        connLog.removeHandler(handler)
    for handler in connHandlers:
        connLog.addHandler(handler)
    connLog.setLevel(logging.DEBUG)

    # Delete conary's log handler since it puts things on stderr and without
    # any timestamps.
    conaryLog = logging.getLogger('conary')
    for handler in conaryLog.handlers:
        conaryLog.removeHandler(handler)

    return rootLog
