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

from threading import RLock

from xobj import xobj

from robj.errors import ExternalUriError
from robj.errors import RemoteInstanceOverwriteError

def require_collection(func):
    def wrapper(self, *args, **kwargs):
        if not self._isCollection:
            raise TypeError
        return func(self, *args, **kwargs)
    return wrapper


class rObj(object):
    """
    rObj object wrapper class.
    """

    __slots__ = ('_uri', '_client', '_doc', '_parent', '_tag', '_isCollection',
        '_dirty', '_dl', '_childTag', )

    def __init__(self, uri, client, doc, parent=None):
        self._uri = uri
        self._client = client
        self._doc = doc
        if parent is not None:
            #self._parent = weakref.ref(parent)
            self._parent = parent
        else:
            self._parent = None

        if self._doc is not None:
            if self._parent and self._parent.isCollection:
                self._tag = self._parent.childTag
            else:
                assert len(self._doc._xobj.elements) == 1
                self._tag = self._doc._xobj.elements[0]
        else:
            self._tag = None

        self._dl = RLock()

        self._childTag = ''
        self._isCollection = False
        if self._tag and self._tag.endswith('s'):
            root = getattr(self._doc, self._tag)
            elements = root._xobj.elements
            if (len(elements) == 1 and self._tag[:-1] in elements):
                element = getattr(root, self._tag[:-1])
                if not isinstance(element, list):
                    setattr(root, self._tag[:-1], [element, ])
                self._childTag = self._tag[:-1]
                self._isCollection = True
        elif isinstance(getattr(self._doc, self._tag, None), list):
            self._isCollection = True

        self._dirty = False

    @property
    def _root(self):
        self._dl.acquire()
        if (self._parent and self._parent.isCollection and
            not isinstance(self._doc, xobj.Document)):
            root = self._doc
        else:
            root = getattr(self._doc, self._tag)
            if self._isCollection and self._childTag:
                root = getattr(root, self._childTag)
            self._dl.release()
        return root

    @property
    def isCollection(self):
        return self._isCollection

    @property
    def parent(self):
        return self._parent

    @property
    def childTag(self):
        return self._childTag

    @property
    def elements(self):
        return self._root._xobj.elements

    def __repr__(self):
        return '<robj.rObj(%s)>' % self._tag

    def _getObj(self, name, value):
        # Wrap this instance with an rObj.
        if hasattr(value, 'id'):
            # Wrap the xobj in an xobj document so that it can be serialized
            # later.
            if isinstance(value, xobj.XObj):
                doc = xobj.Document()
                doc._xobj.elements.append(name)
                setattr(doc, name, value)
            return self.__class__(value.id, self._client, doc, parent=self)

        # Get the instance pointed to by the href.
        elif hasattr(value, 'href'):
            try:
                obj = self._client.do_GET(value.href, parent=self)
            except ExternalUriError:
                return value.href
            return obj

        # Wrap anything that has elements in an rObj.
        elif hasattr(value, '_xobj') and value._xobj.elements:
            return self.__class__(self._uri, self._client, value, parent=self)

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
        if not name.startswith('_'):
            val = getattr(self._root, name)
            obj = self._getObj(name, val)
            if obj:
                return obj
            else:
                return val
        else:
            return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        if not name.startswith('_'):
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
        else:
            object.__setattr__(self, name, value)

    @require_collection
    def __getitem__(self, idx):
        assert isinstance(idx, int), 'index is required to be an interger'

        val = self._root[idx]
        obj = self._getObj(self._childTag, val)
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

    def __len__(self):
        if self._isCollection:
            self._dl.acquire()
            l = len(self._root)
            self._dl.release()
            return l
        else:
            return True

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
