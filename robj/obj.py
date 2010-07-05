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
Module for implementing rObj classes.
"""

class rObj(object):
    """
    Base rObj class.
    """

    __slots__ = ('_uri', '_client', '_doc', '_tag', '_isCollection', '_dirty')

    def __init__(self, uri, client, doc):
        self._uri = uri
        self._client = client
        self._doc = doc

        if self._doc:
            assert len(self._doc._xobj.elements) == 1
            self._tag = self._doc._xobj.elements[0]
        else:
            self._tag = None

        if isinstance(self._doc, list):
            self._isCollection = True
        else:
            self._isCollection = False

        self._dirty = False

    def __getattr__(self, name):
        return object.__getattr__(self, name)

    def __setattr__(self, name, value):
        return object.__setattr__(self, name, value)

    def __getitem__(self, idx):
        pass

    def __setitem__(self, idx, value):
        pass

    def create(self, doc):
        pass

    def persist(self):
        pass

    def delete(self):
        pass

    def refresh(self):
        pass
