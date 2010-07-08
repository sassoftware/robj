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

import weakref
from threading import RLock

from robj.errors import RemoteInstanceOverwriteError

def require_collection(func):
    def wrapper(self, *args, **kwargs):
        if not self._isCollection:
            raise TypeError
        return func(self, *args, **kwargs)
    return wrapper


class rObj(object):
    """
    Base rObj class.
    """

    __slots__ = ('_uri', '_client', '_doc', '_parent', '_tag', '_isCollection',
        '_dirty', '_dl')

    def __init__(self, uri, client, doc, parent=None):
        self._uri = uri
        self._client = client
        self._doc = doc
        if parent:
            self._parent = weakref.ref(parent)
        else:
            self._parent = None

        if self._doc:
            assert len(self._doc._xobj.elements) == 1
            self._tag = self._doc._xobj.elements[0]
        else:
            self._tag = None

        self._dl = RLock()
        if isinstance(self._root, list):
            self._isCollection = True
        else:
            self._isCollection = False

        self._dirty = False

    @property
    def _root(self):
        self._dl.acquire()
        doc = object.__getattr__(self, '_doc')
        tag = object.__getattr__(self, '_tag')
        root = getattr(doc, tag)
        self._dl.release()
        return root

    @property
    def isCollection(self):
        return self._isCollection

    @property
    def parent(self):
        return self._parent

    def _getObj(self, value):
        if hasattr(value, 'id'):
            return self.__class__(value.id, self._client, value, parent=self)
        elif hasattr(value, 'href'):
            obj = self._client.do_GET(value.href, parent=self)
            return obj

        return None

    def _setObj(self, obj, name, value):
        if hasattr(obj, 'href'):
            self._client.do_POST(obj.href, value)
        elif hasattr(obj, 'id'):
            raise RemoteInstanceOverwriteError(
                name=name, uri=self._uri, id=obj.id)
        else:
            return False
        return True

    def __getattr__(self, name):
        try:
            return object.__getattr__(self, name)
        except AttributeError:
            try:
                return getattr(self.__class__, name)
            except AttributeError:
                import epdb; epdb.st()
                val = getattr(self._root, name)
                obj = self._getObj(val)
                if obj:
                    return obj
                else:
                    return val

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        self._dl.acquire()
        if hasattr(self._root, name):
            val = getattr(self._root, name)
            if not self._setObj(val, name, value):
                self._dirty = True
                setattr(self._root, name, value)
        else:
            self._dirty = True
            setattr(self._root, name, value)
        self._dl.release()

    @require_collection
    def __getitem__(self, idx):
        assert isinstance(idx, int), 'index is required to be an interger'

        val = self._root[idx]
        obj = self._getObj(val)
        if obj:
            return obj
        else:
            return val

    @require_collection
    def __setitem__(self, idx, value):
        assert isinstance(idx, int), 'index is required to be an interger'

        # Make sure the current value isn't an instance.
        self._dl.acquire()
        val = self._root.get(idx)
        if hasattr(val, 'id') or hasattr(val, 'href'):
            raise RemoteInstanceOverwriteError(name=idx, uri=self._uri,
                id=hasattr(val, 'id') and val.id or val.href)

        self._root[idx] = value
        self._dl.release()

    @require_collection
    def __delitem__(self, idx):
        assert isinstance(idx, int), 'index is required to be an interger'

        self._dl.acquire()
        val = self._root.get(idx)
        if isinstance(val, self.__class__):
            val.delete()
        elif hasattr(val, 'id'):
            self._client.do_DELETE(val.id)
        else:
            del self._root[idx]
        self._dl.release()

    @require_collection
    def __iter__(self):
        self._dl.acquire()
        for i in range(len(self._root)):
            yield self[i]
        self._dl.release()

    @require_collection
    def append(self, value):
        obj = self._client.do_POST(self._uri, value)
        self._root.append(obj._root)

    def persist(self):
        """
        Update the server with any modifications that have been made to this
        instance.
        """

        if self._dirty:
            self._dl.acquire()
            self._dirty = False
            self._client.do_PUT(self._uri, self._doc)
            self._dl.release()
        else:
            self.refresh()

    def delete(self):
        """
        Delete this instance from the server.
        """

        self._client.do_DELETE(self._uri)

    def refresh(self, force=False):
        """
        Refresh the instance from the server if it is not marked as dirty.
        @param force: Optional parameter (defaults to False) to force the
                      refresh even if the instance is marked as dirty.
        @type force: boolean
        """

        if not self._dirty or force:
            self._dl.acquire()
            self._dirty = False
            self._client.do_GET(self._uri)
            self._dl.release()
