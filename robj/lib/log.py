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

    #connLog = logging.getLogger('robj.http.traffic')
    #for handler in connLog.handlers:
    #    connLog.removeHandler(handler)
    #for handler in connHandlers:
    #    connLog.addHandler(handler)
    #connLog.setLevel(logging.DEBUG)

    # Delete conary's log handler since it puts things on stderr and without
    # any timestamps.
    conaryLog = logging.getLogger('conary')
    for handler in conaryLog.handlers:
        conaryLog.removeHandler(handler)

    return rootLog
