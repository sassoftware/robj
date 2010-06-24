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

class rObjError(Exception):
    """
    Base rObj Error for all other errors to inherit from.
    """

    _params = []
    _template = 'An unknown error has occured.'

    def __init__(self, **kwargs):
        Exception.__init__(self)

        self._kwargs = kwargs

        # Copy kwargs to attributes
        for key in self._params:
           setattr(self, key, kwargs[key])

    def __str__(self):
        return self._template % self.__dict__

    def __repr__(self):
        params = ', '.join('%s=%r' % x for x in self._kwargs.iteritems())
        return '%s(%s)' % (self.__class__, params)
