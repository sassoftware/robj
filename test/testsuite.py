#!/usr/bin/python
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
import os
import sys
import unittest

import bootstrap

from testrunner import pathManager, testhelp


EXCLUDED_PATHS = ['scripts/.*', 'epdb.py', 'stackutil.py', 'test/.*']


def setup():
    xobjPath = pathManager.addExecPath('XOBJ_PATH')
    robjPath = pathManager.addExecPath('ROBJ_PATH')
    pathManager.addResourcePath('TEST_PATH', robjPath + '/test')


def main(argv=None, individual=True):
    if argv is None:
        argv = list(sys.argv)

    from conary.lib import util
    from conary.lib import coveragehook
    sys.excepthook = util.genExcepthook(True, catchSIGUSR1=False)

    handlerClass = testhelp.getHandlerClass(testhelp.ConaryTestSuite,
            lambda handler, environ: os.getenv('ROBJ_PATH'),
            lambda handler, environ: EXCLUDED_PATHS)

    handler = handlerClass(individual=individual)
    results = handler.main(argv)
    return results.getExitCode()


if __name__ == '__main__':
    setup()
    sys.exit(main(sys.argv, individual=False))
